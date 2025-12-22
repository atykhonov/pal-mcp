"""MCP Server implementation."""

from __future__ import annotations

from typing import Any

import uvicorn
from mcp.server import Server
from mcp.server.sse import SseServerTransport

from pal.config import Settings, get_settings, setup_logging
from pal.instructions import ensure_defaults
from pal.tools import register_tools

# Type aliases for ASGI
Scope = dict[str, Any]
Receive = Any
Send = Any


def create_server() -> Server:
    """Create and configure the MCP server.

    Returns:
        Configured MCP server instance.
    """
    server = Server("pal-server")
    register_tools(server)
    return server


def create_app(
    server: Server,
    sse: SseServerTransport,
    settings: Settings,
) -> Any:
    """Create the ASGI application.

    Args:
        server: The MCP server instance.
        sse: The SSE transport.
        settings: Application settings.

    Returns:
        ASGI application callable.
    """

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        """Handle ASGI requests."""
        if scope["type"] != "http":
            return

        path: str = scope["path"]
        method: str = scope["method"]

        # GET /sse - SSE Handshake
        if path == "/sse" and method == "GET":
            print(f"[NET] New Connection from {scope.get('client')}")
            try:
                async with sse.connect_sse(scope, receive, send) as streams:
                    print("[NET] Handshake success. Server running...")
                    await server.run(
                        streams[0],
                        streams[1],
                        server.create_initialization_options(),
                    )
                print("[NET] Connection closed")
            except Exception as e:
                print(f"[NET] Error: {e}")
            return

        # POST /messages - Message handling
        if path == "/messages" and method == "POST":
            print(f"[NET] Message Received! (POST {path})")
            await sse.handle_post_message(scope, receive, send)
            return

        # POST /sse - Claude probe fix
        if path == "/sse" and method == "POST":
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [],
                }
            )
            await send({"type": "http.response.body", "body": b"OK"})
            return

        # GET /files/* - Static file serving
        if path.startswith("/files/") and method == "GET":
            filename = path[len("/files/") :]
            filepath = settings.files_path / filename

            if filepath.exists():
                await send(
                    {
                        "type": "http.response.start",
                        "status": 200,
                        "headers": [(b"content-type", b"text/plain")],
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": filepath.read_bytes(),
                    }
                )
                return

        # 404 Not Found
        await send(
            {
                "type": "http.response.start",
                "status": 404,
                "headers": [],
            }
        )
        await send({"type": "http.response.body", "body": b"Not Found"})

    return app


def run_server(settings: Settings | None = None) -> None:
    """Run the MCP server.

    Args:
        settings: Optional settings override.
    """
    if settings is None:
        settings = get_settings()

    setup_logging(settings)
    ensure_defaults()

    server = create_server()
    sse = SseServerTransport("/messages")
    app = create_app(server, sse, settings)

    print("=" * 60)
    print("PAL MCP SERVER")
    print(f"Listening on {settings.server_host}:{settings.server_port}")
    print("=" * 60)

    uvicorn.run(
        app,
        host=settings.server_host,
        port=settings.server_port,
    )


if __name__ == "__main__":
    run_server()
