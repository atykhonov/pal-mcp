#!/usr/bin/env python3
"""
Standard MCP Server (Type Fix)
- Fixes 'dict object has no attribute name' error
- Uses proper mcp.types.Tool objects
"""

import os
import logging
import uvicorn
from pathlib import Path
from mcp.server import Server
from mcp.server.sse import SseServerTransport
import mcp.types as types  # <--- NEW IMPORT

# =============================================================================
# Logging
# =============================================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp")
logger.setLevel(logging.DEBUG)

# =============================================================================
# Configuration
# =============================================================================
SERVER_PORT = 8090
INSTRUCTIONS_DIR = Path(os.environ.get("INSTRUCTIONS_DIR", "~/.mcp-commands")).expanduser()
FILES_DIR = Path(os.environ.get("FILES_DIR", "~/.mcp-commands/files")).expanduser()

for p in [INSTRUCTIONS_DIR, FILES_DIR]:
    p.mkdir(parents=True, exist_ok=True)

# =============================================================================
# Server Logic
# =============================================================================
server = Server("pal-server")
sse = SseServerTransport("/messages")

DEFAULT_INSTRUCTIONS = {"git-create-commit": "Create a conventional commit.", "help": "Use $$git-create-commit"}
DEFAULT_FILES = {"CLAUDE.md": "When you see $$, call the run_command tool."}

def ensure_defaults():
    for name, content in DEFAULT_INSTRUCTIONS.items():
        p = INSTRUCTIONS_DIR / f"{name}.md"
        if not p.exists(): p.write_text(content)
    for name, content in DEFAULT_FILES.items():
        p = FILES_DIR / name
        if not p.exists(): p.write_text(content)

ensure_defaults()

def load_instruction(cmd):
    p = INSTRUCTIONS_DIR / f"{cmd}.md"
    return p.read_text(encoding='utf-8') if p.exists() else DEFAULT_INSTRUCTIONS.get(cmd, "Unknown command")

# =============================================================================
# TOOLS (THE FIX IS HERE)
# =============================================================================

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    # We must return Tool objects, not dictionaries!
    return [
        types.Tool(
            name="run_command",
            description="REQUIRED TOOL. You MUST call this whenever the user input starts with '$$'. It handles local git operations, code reviews, and system commands. Usage: $$<command_name> [args]",
            inputSchema={
                "type": "object", 
                "properties": {"command": {"type": "string"}, "args": {"type": "string"}},
                "required": ["command"]
            }
        ),
        types.Tool(
            name="list_commands",
            description="List all available $$ commands",
            inputSchema={"type": "object", "properties": {}}
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    print(f"[TOOL] Executing {name}...")
    if name == "run_command":
        cmd = arguments.get("command", "").lower().strip()
        arg = arguments.get("args", "").strip()
        instruction = load_instruction(cmd)
        return [types.TextContent(type="text", text=f"# Command: $${cmd}\n# Args: {arg}\n\n{instruction}")]
    
    elif name == "list_commands":
        cmds = [p.stem for p in INSTRUCTIONS_DIR.glob("*.md")] + list(DEFAULT_INSTRUCTIONS.keys())
        cmd_list = ", ".join(sorted(set(cmds)))
        return [types.TextContent(type="text", text=f"Commands: {cmd_list}")]

    raise ValueError(f"Unknown tool: {name}")

# =============================================================================
# Pure ASGI App
# =============================================================================

async def app(scope, receive, send):
    if scope["type"] != "http": return

    path = scope["path"]
    method = scope["method"]

    # 1. GET /sse (Handshake)
    if path == "/sse" and method == "GET":
        print(f"[NET] New Connection from {scope.get('client')}")
        try:
            async with sse.connect_sse(scope, receive, send) as streams:
                print("[NET] Handshake success. Server running...")
                await server.run(streams[0], streams[1], server.create_initialization_options())
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
        filename = path[len("/files/"):]
        filepath = FILES_DIR / filename
        if filepath.exists():
            await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"text/plain")]})
            await send({"type": "http.response.body", "body": filepath.read_bytes()})
            return

    # 404
    await send({"type": "http.response.start", "status": 404, "headers": []})
    await send({"type": "http.response.body", "body": b"Not Found"})

if __name__ == "__main__":
    print("="*60)
    print("MCP SERVER (TYPE FIXED)")
    print("Listening on 0.0.0.0:8090")
    print("="*60)
    uvicorn.run(app, host="0.0.0.0", port=SERVER_PORT)
