#!/usr/bin/env python3
"""
Standard MCP Server - Modular Version
"""

import uvicorn
from mcp.server import Server
from mcp.server.sse import SseServerTransport

from config import SERVER_PORT, FILES_DIR
from instructions import ensure_defaults
from tools import register_tools

# =============================================================================
# Server Setup
# =============================================================================
server = Server("pal-server")
sse = SseServerTransport("/messages")

# Initialize defaults and register tools
ensure_defaults()
register_tools(server)


# =============================================================================
# Pure ASGI App
# =============================================================================
async def app(scope, receive, send):
    if scope["type"] != "http":
        return

    path = scope["path"]
    method = scope["method"]

    # 1. GET /sse (Handshake)
    if path == "/sse" and method == "GET":
        print(f"[NET] New Connection from {scope.get('client')}")
        try:
            async with sse.connect_sse(scope, receive, send) as streams:
                print("[NET] Handshake success. Server running...")
                await server.run(
                    streams[0], streams[1], server.create_initialization_options()
                )
            print("[NET] Connection closed")
        except Exception as e:
            print(f"[NET] Error: {e}")
        return

    # 2. POST /messages (Data)
    if path == "/messages" and method == "POST":
        print(f"[NET] Message Received! (POST {path})")
        await sse.handle_post_message(scope, receive, send)
        return

    # 3. POST /sse (Claude Probe Fix)
    if path == "/sse" and method == "POST":
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"OK"})
        return

    # 4. GET /files/*
    if path.startswith("/files/") and method == "GET":
        filename = path[len("/files/") :]
        filepath = FILES_DIR / filename
        if filepath.exists():
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"content-type", b"text/plain")],
                }
            )
            await send({"type": "http.response.body", "body": filepath.read_bytes()})
            return

    # 404
    await send({"type": "http.response.start", "status": 404, "headers": []})
    await send({"type": "http.response.body", "body": b"Not Found"})


if __name__ == "__main__":
    print("=" * 60)
    print("MCP SERVER (MODULAR)")
    print(f"Listening on 0.0.0.0:{SERVER_PORT}")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=SERVER_PORT)
