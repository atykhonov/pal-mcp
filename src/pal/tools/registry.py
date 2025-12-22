"""MCP tool registration."""

from __future__ import annotations

from typing import TYPE_CHECKING

import mcp.types as types

from pal.instructions import list_available_commands
from pal.tools.handlers import execute_command
from pal.tools.parser import parse_command, parse_pipeline

if TYPE_CHECKING:
    from mcp.server import Server


# Tool descriptions
RUN_PAL_COMMAND_DESCRIPTION: str = (
    "REQUIRED TOOL. You MUST call this whenever the user "
    "input starts with '$$'. Do NOT call list_pal_commands, "
    "call THIS tool instead. Pass everything after '$$' as "
    "the command parameter. Examples: "
    "'$$tr Hello' -> command='tr Hello'. "
    "'$$prompt tr' -> command='prompt tr' (shows prompt definition). "
    "'$$git commit' -> command='git commit'. "
    "When saving prompts with '$$prompt <name> <instruction>', "
    "convert all newlines in the instruction to literal \\n characters. "
    "IMPORTANT: Variable substitution - before calling this tool, replace: "
    "$MSG = user's previous message, "
    "$REPLY = your (LLM's) previous response. "
    "Any '## Heading' in your response creates a variable: "
    "'## Summary' -> $SUMMARY, '## Translation' -> $TRANSLATION, "
    "'## Corrected Text' -> $CORRECTED_TEXT, etc. "
    "The variable contains the content under that heading."
)

LIST_PAL_COMMANDS_DESCRIPTION: str = "List all available $$ commands"


def register_tools(server: Server) -> None:
    """Register all MCP tools with the server.

    Args:
        server: The MCP server instance.
    """

    @server.list_tools()  # type: ignore[misc]
    async def list_tools() -> list[types.Tool]:
        """Return the list of available tools."""
        return [
            types.Tool(
                name="run_pal_command",
                description=RUN_PAL_COMMAND_DESCRIPTION,
                inputSchema={
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": (
                                "The full command string "
                                "(e.g., 'git commit' or 'git commit | review')"
                            ),
                        },
                    },
                    "required": ["command"],
                },
            ),
            types.Tool(
                name="list_pal_commands",
                description=LIST_PAL_COMMANDS_DESCRIPTION,
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    @server.call_tool()  # type: ignore[misc]
    async def call_tool(
        name: str, arguments: dict[str, str]
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Handle tool execution.

        Args:
            name: The tool name.
            arguments: The tool arguments.

        Returns:
            List of content items.

        Raises:
            ValueError: If the tool name is unknown.
        """
        print(f"[TOOL] Executing {name}...")

        if name == "run_pal_command":
            return _handle_run_command(arguments)

        if name == "list_pal_commands":
            return _handle_list_commands()

        raise ValueError(f"Unknown tool: {name}")


def _handle_run_command(
    arguments: dict[str, str],
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle the run_pal_command tool.

    Args:
        arguments: The tool arguments containing the command.

    Returns:
        List of text content with the command results.
    """
    command_string = arguments.get("command", "").strip()
    pipeline = parse_pipeline(command_string)

    if not pipeline:
        return [types.TextContent(type="text", text="Error: No command provided")]

    results: list[str] = []

    for raw_command in pipeline:
        parsed = parse_command(raw_command)
        output = execute_command(parsed)
        results.append(output)

    output_text = "\n\n---\n\n".join(results)
    return [types.TextContent(type="text", text=output_text)]


def _handle_list_commands() -> (
    list[types.TextContent | types.ImageContent | types.EmbeddedResource]
):
    """Handle the list_pal_commands tool.

    Returns:
        List of text content with available commands.
    """
    commands = list_available_commands()
    command_list = ", ".join(commands)
    return [types.TextContent(type="text", text=f"Commands: {command_list}")]
