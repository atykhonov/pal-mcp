"""MCP Server implementation."""

from __future__ import annotations

import asyncio
import json
import secrets
from typing import Any
from urllib.parse import parse_qs, urlencode

import uvicorn
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.server.streamable_http import StreamableHTTPServerTransport
from mcp.server.stdio import stdio_server

from pal.config import Settings, get_settings, setup_logging
from pal.prompts import ensure_defaults
from pal.oauth import get_oauth_manager
from pal.tools import register_tools

# Type aliases for ASGI
Scope = dict[str, Any]
Receive = Any
Send = Any


# Server instructions sent to clients during MCP initialization
SERVER_INSTRUCTIONS = "When you see $$ at the start of user input, call run_pal_command with the command text."


def create_server() -> Server:
    """Create and configure the MCP server.

    Returns:
        Configured MCP server instance.
    """
    server = Server("pal-server", instructions=SERVER_INSTRUCTIONS)
    register_tools(server)
    return server


class MCPApp:
    """ASGI application with OAuth and MCP support."""

    def __init__(self, server: Server, settings: Settings) -> None:
        self.server = server
        self.settings = settings
        self.oauth = get_oauth_manager(settings)
        # Transport for Streamable HTTP (Claude Desktop/Web)
        self._streamable_transports: dict[str, StreamableHTTPServerTransport] = {}
        # Transport for legacy SSE (Claude Code)
        self._sse_transport = SseServerTransport("/messages")
        self._server_tasks: dict[str, asyncio.Task] = {}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle ASGI requests."""
        if scope["type"] != "http":
            return

        path: str = scope["path"]
        method: str = scope["method"]

        # OAuth Metadata Discovery
        if path == "/.well-known/oauth-authorization-server" and method == "GET":
            await self._json_response(send, self.oauth.get_metadata())
            return

        # Protected Resource Metadata (RFC 9470)
        if path.startswith("/.well-known/oauth-protected-resource") and method == "GET":
            base_url = self.settings.oauth_public_url or f"http://localhost:{self.settings.server_port}"
            await self._json_response(send, {
                "resource": base_url,
                "authorization_servers": [base_url],
            })
            return

        # Dynamic Client Registration (RFC 7591)
        if path == "/register" and method == "POST":
            await self._handle_register(scope, receive, send)
            return

        # Authorization Endpoint
        if path == "/authorize" and method == "GET":
            await self._handle_authorize(scope, send)
            return

        # Token Endpoint
        if path == "/token" and method == "POST":
            await self._handle_token(scope, receive, send)
            return

        # MCP endpoint - /sse or /mcp
        if path in ("/sse", "/mcp"):
            await self._handle_mcp(scope, receive, send)
            return

        # POST /messages - Legacy SSE message handling
        if path.startswith("/messages") and method == "POST":
            if not self._is_authenticated(scope):
                await self._error_response(send, "unauthorized", "Authentication required", 401)
                return
            await self._sse_transport.handle_post_message(scope, receive, send)
            return

        # GET /files/* - Static file serving
        if path.startswith("/files/") and method == "GET":
            await self._handle_files(path, send)
            return

        # 404 Not Found
        await self._send_status(send, 404, b"Not Found")

    async def _handle_mcp(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle MCP requests using appropriate transport."""
        method = scope["method"]
        client_ip, is_proxied = self._get_client_ip(scope)
        token = self._get_authorization_header(scope)

        print(f"[MCP] {method} from {client_ip} (proxied={is_proxied}, token={token is not None})")

        # Check authentication
        if not self._is_authenticated(scope):
            print(f"[MCP] Unauthorized from {client_ip}")
            await send({
                "type": "http.response.start",
                "status": 401,
                "headers": [(b"www-authenticate", b"Bearer")],
            })
            await send({"type": "http.response.body", "body": b"Authentication required"})
            return

        # Check Accept header to determine transport type
        accept = ""
        for name, value in scope.get("headers", []):
            if name == b"accept":
                accept = value.decode()
                break

        # Streamable HTTP requires Accept with BOTH application/json AND text/event-stream
        # Legacy SSE only has text/event-stream
        is_streamable_http = "application/json" in accept and "text/event-stream" in accept

        if method == "POST":
            # POST always goes to Streamable HTTP
            await self._handle_streamable_http(scope, receive, send)
        elif method == "GET" and is_streamable_http:
            # GET with both accept types = Streamable HTTP
            await self._handle_streamable_http(scope, receive, send)
        elif method == "GET":
            # GET without application/json = Legacy SSE (Claude Code)
            print(f"[MCP] Routing to legacy SSE (accept={accept})")
            await self._handle_legacy_sse(scope, receive, send)
        else:
            await self._send_status(send, 405, b"Method Not Allowed")

    async def _handle_streamable_http(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle Streamable HTTP transport requests."""
        # Get session ID from headers
        session_id = None
        for name, value in scope.get("headers", []):
            if name == b"mcp-session-id":
                session_id = value.decode()
                break

        # Get existing transport for this session
        if session_id and session_id in self._streamable_transports:
            transport = self._streamable_transports[session_id]
            print(f"[MCP] Using existing session: {session_id}")
        else:
            # Generate new session ID
            new_session_id = secrets.token_hex(16)
            print(f"[MCP] Creating new session: {new_session_id}")

            # Create new transport with explicit session ID
            transport = StreamableHTTPServerTransport(mcp_session_id=new_session_id)
            ready_event = asyncio.Event()

            async def run_server():
                try:
                    async with transport.connect() as (read_stream, write_stream):
                        # Signal that transport is ready
                        ready_event.set()
                        print(f"[MCP] Session ready: {new_session_id}")
                        await self.server.run(
                            read_stream,
                            write_stream,
                            self.server.create_initialization_options(),
                        )
                    print(f"[MCP] Session ended: {new_session_id}")
                except Exception as e:
                    print(f"[MCP] Session error ({new_session_id}): {e}")
                    ready_event.set()  # Unblock even on error
                finally:
                    # Clean up session
                    self._streamable_transports.pop(new_session_id, None)
                    self._server_tasks.pop(new_session_id, None)

            # Start server task
            task = asyncio.create_task(run_server())

            # Store transport before waiting
            self._streamable_transports[new_session_id] = transport
            self._server_tasks[new_session_id] = task

            # Wait for transport to be ready
            await ready_event.wait()

        # Handle the request
        try:
            await transport.handle_request(scope, receive, send)
        except Exception as e:
            print(f"[MCP] Error handling request: {e}")
            import traceback
            traceback.print_exc()
            await self._send_status(send, 500, str(e).encode())

    async def _handle_legacy_sse(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle legacy SSE transport (for Claude Code)."""
        print("[NET] Legacy SSE connection")
        try:
            async with self._sse_transport.connect_sse(scope, receive, send) as streams:
                print("[NET] SSE Handshake success")
                await self.server.run(
                    streams[0],
                    streams[1],
                    self.server.create_initialization_options(),
                )
            print("[NET] SSE Connection closed")
        except Exception as e:
            print(f"[NET] SSE Error: {e}")

    async def _handle_register(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle client registration."""
        body = await self._read_body(receive)
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            await self._error_response(send, "invalid_request", "Invalid JSON body")
            return

        client_name = data.get("client_name", "Unknown Client")
        redirect_uris = data.get("redirect_uris", [])

        if not redirect_uris:
            await self._error_response(send, "invalid_request", "redirect_uris is required")
            return

        client = self.oauth.register_client(client_name, redirect_uris)
        await self._json_response(send, {
            "client_id": client.client_id,
            "client_name": client.client_name,
            "redirect_uris": client.redirect_uris,
        }, 201)

    async def _handle_authorize(self, scope: Scope, send: Send) -> None:
        """Handle authorization request."""
        params = self._get_query_params(scope)
        client_id = params.get("client_id", "")
        redirect_uri = params.get("redirect_uri", "")
        response_type = params.get("response_type", "")
        state = params.get("state", "")
        code_challenge = params.get("code_challenge", "")
        code_challenge_method = params.get("code_challenge_method", "S256")

        if response_type != "code":
            await self._error_response(send, "unsupported_response_type", "Only 'code' is supported")
            return

        if not code_challenge:
            await self._error_response(send, "invalid_request", "code_challenge required (PKCE)")
            return

        # Auto-register client if not exists
        if not self.oauth.get_client(client_id):
            self.oauth.register_client(f"Auto: {client_id}", [redirect_uri])

        if not self.oauth.validate_redirect_uri(client_id, redirect_uri):
            await self._error_response(send, "invalid_request", "Invalid redirect_uri")
            return

        # Auto-approve for personal use
        code = self.oauth.create_authorization_code(
            client_id=client_id,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
        )

        redirect_params = {"code": code}
        if state:
            redirect_params["state"] = state
        redirect_url = f"{redirect_uri}?{urlencode(redirect_params)}"
        print(f"[OAUTH] Redirecting to: {redirect_url}")
        await self._redirect_response(send, redirect_url)

    async def _handle_token(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle token exchange."""
        body = await self._read_body(receive)
        content_type = ""
        for name, value in scope.get("headers", []):
            if name == b"content-type":
                content_type = value.decode()
                break

        if "application/json" in content_type:
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                await self._error_response(send, "invalid_request", "Invalid JSON")
                return
        else:
            data = {k: v[0] for k, v in parse_qs(body.decode()).items()}

        grant_type = data.get("grant_type", "")
        if grant_type != "authorization_code":
            await self._error_response(send, "unsupported_grant_type", "Only authorization_code supported")
            return

        code = data.get("code", "")
        client_id = data.get("client_id", "")
        redirect_uri = data.get("redirect_uri", "")
        code_verifier = data.get("code_verifier", "")

        if not all([code, client_id, code_verifier]):
            await self._error_response(send, "invalid_request", "Missing required parameters")
            return

        access_token = self.oauth.exchange_code(code, client_id, redirect_uri, code_verifier)
        if not access_token:
            await self._error_response(send, "invalid_grant", "Invalid code or verifier", 400)
            return

        await self._json_response(send, {
            "access_token": access_token.token,
            "token_type": "Bearer",
            "expires_in": access_token.expires_in,
        })

    async def _handle_files(self, path: str, send: Send) -> None:
        """Handle static file serving."""
        filename = path[len("/files/"):]
        filepath = self.settings.files_path / filename

        if filepath.exists():
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/plain")],
            })
            await send({"type": "http.response.body", "body": filepath.read_bytes()})
        else:
            await self._send_status(send, 404, b"Not Found")

    def _is_authenticated(self, scope: Scope) -> bool:
        """Check if request is authenticated."""
        token = self._get_authorization_header(scope)
        if token:
            is_valid = self.oauth.validate_token(token)
            print(f"[AUTH] Token validation: {is_valid}, token prefix: {token[:20] if len(token) > 20 else token}...")
            if is_valid:
                return True

        client_ip, is_proxied = self._get_client_ip(scope)
        if not is_proxied and self.oauth.is_ip_allowed(client_ip):
            return True

        return False

    def _get_client_ip(self, scope: Scope) -> tuple[str, bool]:
        """Extract client IP. Returns (ip, is_proxied)."""
        for name, value in scope.get("headers", []):
            if name in (b"x-forwarded-for", b"x-real-ip"):
                return value.decode().split(",")[0].strip(), True
        client = scope.get("client")
        if client:
            return client[0], False
        return "", False

    def _get_authorization_header(self, scope: Scope) -> str | None:
        """Extract Bearer token from Authorization header."""
        for name, value in scope.get("headers", []):
            if name == b"authorization":
                auth = value.decode()
                if auth.startswith("Bearer "):
                    return auth[7:]
        return None

    def _get_query_params(self, scope: Scope) -> dict[str, str]:
        """Parse query string parameters."""
        qs = scope.get("query_string", b"").decode()
        params = parse_qs(qs)
        return {k: v[0] for k, v in params.items()}

    async def _read_body(self, receive: Receive) -> bytes:
        """Read full request body."""
        body = b""
        while True:
            message = await receive()
            body += message.get("body", b"")
            if not message.get("more_body", False):
                break
        return body

    async def _json_response(self, send: Send, data: dict, status: int = 200) -> None:
        """Send JSON response."""
        body = json.dumps(data).encode()
        await send({
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"cache-control", b"no-store"),
            ],
        })
        await send({"type": "http.response.body", "body": body})

    async def _error_response(self, send: Send, error: str, desc: str, status: int = 400) -> None:
        """Send OAuth error response."""
        await self._json_response(send, {"error": error, "error_description": desc}, status)

    async def _redirect_response(self, send: Send, location: str) -> None:
        """Send redirect response."""
        await send({
            "type": "http.response.start",
            "status": 302,
            "headers": [(b"location", location.encode())],
        })
        await send({"type": "http.response.body", "body": b""})

    async def _send_status(self, send: Send, status: int, body: bytes) -> None:
        """Send simple status response."""
        await send({"type": "http.response.start", "status": status, "headers": []})
        await send({"type": "http.response.body", "body": body})


async def run_stdio_server(settings: Settings) -> None:
    """Run the MCP server with stdio transport."""
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def run_sse_server(settings: Settings) -> None:
    """Run the MCP server with SSE/Streamable HTTP transport."""
    server = create_server()
    app = MCPApp(server, settings)

    protocol = "https" if settings.ssl_certfile else "http"
    print("=" * 60)
    print("PAL MCP SERVER")
    print(f"Listening on {protocol}://{settings.server_host}:{settings.server_port}")
    print("=" * 60)

    ssl_kwargs = {}
    if settings.ssl_certfile and settings.ssl_keyfile:
        ssl_kwargs["ssl_certfile"] = str(settings.ssl_certfile.expanduser())
        ssl_kwargs["ssl_keyfile"] = str(settings.ssl_keyfile.expanduser())

    uvicorn.run(
        app,
        host=settings.server_host,
        port=settings.server_port,
        **ssl_kwargs,
    )


def run_server(settings: Settings | None = None) -> None:
    """Run the MCP server."""
    if settings is None:
        settings = get_settings()

    setup_logging(settings)
    ensure_defaults()

    if settings.transport == "stdio":
        asyncio.run(run_stdio_server(settings))
    else:
        run_sse_server(settings)


if __name__ == "__main__":
    run_server()
