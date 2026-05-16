"""MCP Server implementation using FastMCP + Starlette."""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import parse_qs, urlencode

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.routing import Mount, Route

from pal.config import Settings, get_settings, setup_logging
from pal.oauth import OAuthManager, get_oauth_manager
from pal.prompts import ensure_defaults
from pal.tools import mcp


class AuthMiddleware:
    """ASGI middleware that enforces OAuth/IP-based authentication."""

    def __init__(self, app: Any, oauth: OAuthManager, settings: Settings) -> None:
        self.app = app
        self.oauth = oauth
        self.settings = settings

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if not self._is_authenticated(scope):
            client_ip, _ = self._get_client_ip(scope)
            print(f"[AUTH] Unauthorized from {client_ip}")
            response = Response(
                "Authentication required",
                status_code=401,
                headers={"www-authenticate": "Bearer"},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)

    def _is_authenticated(self, scope: dict[str, Any]) -> bool:
        token = self._get_bearer_token(scope)
        if token:
            is_valid = self.oauth.validate_token(token)
            print(
                f"[AUTH] Token validation: {is_valid}, token prefix: {token[:20] if len(token) > 20 else token}..."
            )
            if is_valid:
                return True
        client_ip, is_proxied = self._get_client_ip(scope)
        return not is_proxied and self.oauth.is_ip_allowed(client_ip)

    def _get_bearer_token(self, scope: dict[str, Any]) -> str | None:
        for name, value in scope.get("headers", []):
            if name == b"authorization":
                auth = value.decode()
                if auth.startswith("Bearer "):
                    return str(auth[7:])
        return None

    def _get_client_ip(self, scope: dict[str, Any]) -> tuple[str, bool]:
        for name, value in scope.get("headers", []):
            if name in (b"x-forwarded-for", b"x-real-ip"):
                return value.decode().split(",")[0].strip(), True
        client = scope.get("client")
        if client:
            return client[0], False
        return "", False


def _create_oauth_routes(oauth: OAuthManager, settings: Settings) -> list[Route]:
    """Create Starlette routes for OAuth endpoints."""

    async def oauth_metadata(request: Request) -> JSONResponse:  # noqa: ARG001
        return JSONResponse(oauth.get_metadata())

    async def protected_resource_metadata(
        request: Request,  # noqa: ARG001
    ) -> JSONResponse:
        base_url = (
            settings.oauth_public_url or f"http://localhost:{settings.server_port}"
        )
        return JSONResponse(
            {
                "resource": base_url,
                "authorization_servers": [base_url],
            }
        )

    async def handle_register(request: Request) -> JSONResponse:
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return JSONResponse(
                {"error": "invalid_request", "error_description": "Invalid JSON body"},
                status_code=400,
            )
        client_name = data.get("client_name", "Unknown Client")
        redirect_uris = data.get("redirect_uris", [])
        if not redirect_uris:
            return JSONResponse(
                {
                    "error": "invalid_request",
                    "error_description": "redirect_uris is required",
                },
                status_code=400,
            )
        client = oauth.register_client(client_name, redirect_uris)
        return JSONResponse(
            {
                "client_id": client.client_id,
                "client_name": client.client_name,
                "redirect_uris": client.redirect_uris,
            },
            status_code=201,
        )

    async def handle_authorize(request: Request) -> Response:
        params = dict(request.query_params)
        client_id = params.get("client_id", "")
        redirect_uri = params.get("redirect_uri", "")
        response_type = params.get("response_type", "")
        state = params.get("state", "")
        code_challenge = params.get("code_challenge", "")
        code_challenge_method = params.get("code_challenge_method", "S256")

        if response_type != "code":
            return JSONResponse(
                {
                    "error": "unsupported_response_type",
                    "error_description": "Only 'code' is supported",
                },
                status_code=400,
            )
        if not code_challenge:
            return JSONResponse(
                {
                    "error": "invalid_request",
                    "error_description": "code_challenge required (PKCE)",
                },
                status_code=400,
            )
        if not oauth.get_client(client_id):
            oauth.register_client(f"Auto: {client_id}", [redirect_uri])
        if not oauth.validate_redirect_uri(client_id, redirect_uri):
            return JSONResponse(
                {
                    "error": "invalid_request",
                    "error_description": "Invalid redirect_uri",
                },
                status_code=400,
            )
        code = oauth.create_authorization_code(
            client_id=client_id,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
        )
        redirect_params: dict[str, str] = {"code": code}
        if state:
            redirect_params["state"] = state
        redirect_url = f"{redirect_uri}?{urlencode(redirect_params)}"
        print(f"[OAUTH] Redirecting to: {redirect_url}")
        return RedirectResponse(redirect_url, status_code=302)

    async def handle_token(request: Request) -> JSONResponse:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                data = await request.json()
            except json.JSONDecodeError:
                return JSONResponse(
                    {"error": "invalid_request", "error_description": "Invalid JSON"},
                    status_code=400,
                )
        else:
            body = await request.body()
            data = {k: v[0] for k, v in parse_qs(body.decode()).items()}

        grant_type = data.get("grant_type", "")
        if grant_type != "authorization_code":
            return JSONResponse(
                {
                    "error": "unsupported_grant_type",
                    "error_description": "Only authorization_code supported",
                },
                status_code=400,
            )
        code = data.get("code", "")
        client_id = data.get("client_id", "")
        redirect_uri = data.get("redirect_uri", "")
        code_verifier = data.get("code_verifier", "")
        if not all([code, client_id, code_verifier]):
            return JSONResponse(
                {
                    "error": "invalid_request",
                    "error_description": "Missing required parameters",
                },
                status_code=400,
            )
        access_token = oauth.exchange_code(code, client_id, redirect_uri, code_verifier)
        if not access_token:
            return JSONResponse(
                {
                    "error": "invalid_grant",
                    "error_description": "Invalid code or verifier",
                },
                status_code=400,
            )
        return JSONResponse(
            {
                "access_token": access_token.token,
                "token_type": "Bearer",
                "expires_in": access_token.expires_in,
            }
        )

    return [
        Route(
            "/.well-known/oauth-authorization-server",
            oauth_metadata,
            methods=["GET"],
        ),
        Route(
            "/.well-known/oauth-protected-resource",
            protected_resource_metadata,
            methods=["GET"],
        ),
        Route("/register", handle_register, methods=["POST"]),
        Route("/authorize", handle_authorize, methods=["GET"]),
        Route("/token", handle_token, methods=["POST"]),
    ]


def _create_file_route(settings: Settings) -> Route:
    """Create Starlette route for static file serving."""

    async def handle_files(request: Request) -> Response:
        path = request.path_params["path"]
        filepath = settings.files_path / path
        if filepath.exists():
            return Response(filepath.read_bytes(), media_type="text/plain")
        return Response("Not Found", status_code=404)

    return Route("/files/{path:path}", handle_files, methods=["GET"])


def create_app(settings: Settings | None = None) -> Starlette:
    """Create the Starlette ASGI application.

    Mounts FastMCP transport apps with auth middleware,
    OAuth endpoints, and static file serving.
    """
    if settings is None:
        settings = get_settings()

    oauth = get_oauth_manager(settings)

    # Both transports use non-overlapping paths:
    #   SSE: /sse (GET), /messages (POST)
    #   Streamable HTTP: /mcp (POST/GET)
    # Combine into one Starlette sub-app, wrap with auth, mount at "/"
    combined_mcp = Starlette(
        routes=[*mcp.sse_app().routes, *mcp.streamable_http_app().routes]
    )
    authed_mcp = AuthMiddleware(combined_mcp, oauth, settings)

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:  # noqa: ARG001
        async with mcp.session_manager.run():
            yield

    routes: list[Route | Mount] = [
        # OAuth (unauthenticated)
        *_create_oauth_routes(oauth, settings),
        # Static files (unauthenticated)
        _create_file_route(settings),
        # MCP transports (authenticated): /mcp, /sse, /messages
        Mount("/", app=authed_mcp),  # type: ignore[arg-type]
    ]

    return Starlette(routes=routes, lifespan=lifespan)


async def run_stdio_server(settings: Settings) -> None:  # noqa: ARG001
    """Run the MCP server with stdio transport."""
    await mcp.run_stdio_async()


def run_sse_server(settings: Settings) -> None:
    """Run the MCP server with SSE/Streamable HTTP transport."""
    app = create_app(settings)

    protocol = "https" if settings.ssl_certfile else "http"
    print("=" * 60)
    print("PAL MCP SERVER")
    print(f"Listening on {protocol}://{settings.server_host}:{settings.server_port}")
    print("=" * 60)

    ssl_kwargs: dict[str, Any] = {}
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
