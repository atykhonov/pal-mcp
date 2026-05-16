"""MCP tool registration using FastMCP."""

from __future__ import annotations

import json

from mcp.server.fastmcp import Context, FastMCP

from pal.config import get_settings
from pal.prompts import (
    list_available_commands,
    list_custom_prompts,
    load_custom_prompt,
    load_prompt,
)
from pal.tools.curl import execute_curl
from pal.tools.handlers import execute_command
from pal.tools.parser import parse_command

SERVER_INSTRUCTIONS = (
    "When you see $$ at the start of user input, "
    "call run_pal_command with the command text."
)

mcp = FastMCP("pal-server", instructions=SERVER_INSTRUCTIONS)


@mcp.tool()
async def run_pal_command(command: str, ctx: Context) -> str:
    """Execute a PAL $$ command. For built-in commands (echo, prompt, help): executes and returns result. For prompt-based commands: returns bundled prompts for you to follow."""
    command = command.strip()
    if not command:
        return "Error: No command provided"

    print(f"[TOOL] Executing run_pal_command...")
    parsed = parse_command(command)
    return await execute_command(parsed, ctx.request_context)


@mcp.tool()
async def list_pal_commands() -> str:
    """List all available $$ commands."""
    print("[TOOL] Executing list_pal_commands...")
    commands = list_available_commands()
    return f"Commands: {', '.join(commands)}"


@mcp.tool()
async def read_pal_resource(uri: str) -> str:
    """Read PAL resource files (prompt definitions). Returns the content of the specified prompt file."""
    uri = uri.strip()
    if not uri:
        return "Error: URI is required"

    print("[TOOL] Executing read_pal_resource...")
    content: str | None = None

    if uri.startswith("pal://prompts/custom/"):
        name = uri[len("pal://prompts/custom/") :].removesuffix(".md")
        content = load_custom_prompt(name)
    elif uri.startswith("pal://prompts/"):
        rel_path = uri[len("pal://prompts/") :]
        parts = rel_path.removesuffix(".md").split("/")
        if len(parts) == 1:
            content = load_prompt(parts[0])
            if content.startswith("Unknown command:"):
                content = None
        elif len(parts) == 2:
            content = load_prompt(parts[0], parts[1])
            if content.startswith("Unknown command:"):
                content = None
        else:
            settings = get_settings()
            file_path = settings.prompts_path / rel_path
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")

    if content is None:
        return f"Error: Resource not found: {uri}"
    return content


@mcp.tool()
async def list_pal_resources() -> str:
    """List all available PAL prompt resources. Returns URIs that can be used with read_pal_resource."""
    print("[TOOL] Executing list_pal_resources...")
    resources: list[str] = []
    settings = get_settings()

    prompts_path = settings.prompts_path
    if prompts_path.exists():
        for path in sorted(prompts_path.rglob("*.md")):
            rel_path = path.relative_to(prompts_path)
            if rel_path.parts and rel_path.parts[0] == "custom":
                continue
            resources.append(f"pal://prompts/{rel_path}")

    for name in list_custom_prompts():
        resources.append(f"pal://prompts/custom/{name}.md")

    return "Available resources:\n" + "\n".join(f"  - {r}" for r in resources)


@mcp.tool()
def pal_curl(command: str, timeout: int = 30) -> str:
    """Execute a curl command on the server. Pass the full curl command string (e.g., 'curl -s http://localhost:7700/health'). All standard curl flags are supported. Returns JSON with 'success', 'output', and optionally 'error'."""
    print("[TOOL] Executing pal_curl...")
    result = execute_curl(command=command, timeout=timeout)
    return json.dumps(result, indent=2)
