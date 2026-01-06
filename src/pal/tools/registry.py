"""MCP tool and resource registration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import mcp.types as types
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server.lowlevel.server import request_ctx

from pal.config import get_settings
from pal.instructions import (
    list_available_commands,
    list_custom_prompts,
    load_custom_prompt,
    load_instruction,
)
from pal.tools.handlers import execute_command
from pal.tools.curl import execute_curl
from pal.tools.parser import parse_command, parse_pipeline

if TYPE_CHECKING:
    from mcp.server import Server


# Tool descriptions
RUN_PAL_COMMAND_DESCRIPTION: str = (
    "Execute a PAL command or get instructions for it. "
    "For built-in commands (echo, lorem-ipsum, prompt, help): executes directly. "
    "For other commands (notes, git): returns instruction markdown - "
    "read the instructions and use the curl tool to execute API calls. "
    "Variable substitution: $MSG = user's previous message, "
    "$REPLY = your previous response. "
    "Headings create variables: '## Summary' -> $SUMMARY."
)

LIST_PAL_COMMANDS_DESCRIPTION: str = "List all available $$ commands"

READ_PAL_RESOURCE_DESCRIPTION: str = (
    "Read PAL resource files. "
    "For $$ commands, first read pal://instructions/root.md which describes the protocol."
)

LIST_PAL_RESOURCES_DESCRIPTION: str = (
    "List all available PAL resources (prompts and instructions). "
    "Returns URIs that can be used with read_pal_resource."
)

# Granular notes tool descriptions - DISABLED (using curl tool + instruction files instead)
# These tools return raw JSON data. Read pal://instructions/notes/<subcommand>.md first
# to understand how to format the output for the user.
# NOTES_LIST_DESCRIPTION: str = (
#     "List recent notes. Returns JSON with 'success' and 'notes' array. "
#     "Read pal://instructions/notes/list.md for output formatting."
# )
#
# NOTES_ADD_DESCRIPTION: str = (
#     "Add a new note. Returns JSON with 'success' and 'note' object. "
#     "Read pal://instructions/notes/add.md for output formatting."
# )
#
# NOTES_VIEW_DESCRIPTION: str = (
#     "View a note by ID (full or partial UUID). Returns JSON with 'success' and 'note'. "
#     "Read pal://instructions/notes/view.md for output formatting."
# )
#
# NOTES_DELETE_DESCRIPTION: str = (
#     "Delete a note by ID. Returns JSON with 'success' and 'deleted_note'. "
#     "Read pal://instructions/notes/delete.md for output formatting."
# )
#
# NOTES_TAGS_DESCRIPTION: str = (
#     "Update tags on a note. Returns JSON with 'success', 'note', and 'old_tags'. "
#     "Read pal://instructions/notes/tags.md for output formatting."
# )
#
# NOTES_SEARCH_DESCRIPTION: str = (
#     "Full-text search. Returns JSON with 'success', 'hits', and 'query'. "
#     "Read pal://instructions/notes/search.md for output formatting."
# )
#
# NOTES_AI_SEARCH_DESCRIPTION: str = (
#     "AI semantic search using embeddings. Returns JSON with 'success', 'hits', 'query', 'semantic_hit_count'. "
#     "Read pal://instructions/notes/ai.md for output formatting."
# )

CURL_DESCRIPTION: str = (
    "Execute a curl command on the server. "
    "Pass the full curl command string (e.g., 'curl -s http://localhost:7700/health'). "
    "All standard curl flags are supported. "
    "Returns JSON with 'success', 'output', and optionally 'error'."
)


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
            types.Tool(
                name="read_pal_resource",
                description=READ_PAL_RESOURCE_DESCRIPTION,
                inputSchema={
                    "type": "object",
                    "properties": {
                        "uri": {
                            "type": "string",
                            "description": (
                                "The resource URI "
                                "(e.g., 'pal://instructions/notes.md' or 'pal://prompts/tr.md')"
                            ),
                        },
                    },
                    "required": ["uri"],
                },
            ),
            types.Tool(
                name="list_pal_resources",
                description=LIST_PAL_RESOURCES_DESCRIPTION,
                inputSchema={"type": "object", "properties": {}},
            ),
            # Granular notes tools - DISABLED (using curl tool + instruction files instead)
            # types.Tool(
            #     name="notes_list",
            #     description=NOTES_LIST_DESCRIPTION,
            #     inputSchema={
            #         "type": "object",
            #         "properties": {
            #             "tags": {
            #                 "type": "array",
            #                 "items": {"type": "string"},
            #                 "description": "Optional tags to filter by",
            #             },
            #             "limit": {
            #                 "type": "integer",
            #                 "description": "Maximum number of notes to return (default 10)",
            #             },
            #         },
            #     },
            # ),
            # types.Tool(
            #     name="notes_add",
            #     description=NOTES_ADD_DESCRIPTION,
            #     inputSchema={
            #         "type": "object",
            #         "properties": {
            #             "content": {
            #                 "type": "string",
            #                 "description": "The note content",
            #             },
            #             "tags": {
            #                 "type": "array",
            #                 "items": {"type": "string"},
            #                 "description": "Optional tags for the note",
            #             },
            #         },
            #         "required": ["content"],
            #     },
            # ),
            # types.Tool(
            #     name="notes_view",
            #     description=NOTES_VIEW_DESCRIPTION,
            #     inputSchema={
            #         "type": "object",
            #         "properties": {
            #             "note_id": {
            #                 "type": "string",
            #                 "description": "Full or partial UUID of the note",
            #             },
            #         },
            #         "required": ["note_id"],
            #     },
            # ),
            # types.Tool(
            #     name="notes_delete",
            #     description=NOTES_DELETE_DESCRIPTION,
            #     inputSchema={
            #         "type": "object",
            #         "properties": {
            #             "note_id": {
            #                 "type": "string",
            #                 "description": "Full or partial UUID of the note to delete",
            #             },
            #         },
            #         "required": ["note_id"],
            #     },
            # ),
            # types.Tool(
            #     name="notes_tags",
            #     description=NOTES_TAGS_DESCRIPTION,
            #     inputSchema={
            #         "type": "object",
            #         "properties": {
            #             "note_id": {
            #                 "type": "string",
            #                 "description": "Full or partial UUID of the note",
            #             },
            #             "tags": {
            #                 "type": "array",
            #                 "items": {"type": "string"},
            #                 "description": "New tags to set on the note",
            #             },
            #         },
            #         "required": ["note_id", "tags"],
            #     },
            # ),
            # types.Tool(
            #     name="notes_search",
            #     description=NOTES_SEARCH_DESCRIPTION,
            #     inputSchema={
            #         "type": "object",
            #         "properties": {
            #             "query": {
            #                 "type": "string",
            #                 "description": "Search query",
            #             },
            #             "tags": {
            #                 "type": "array",
            #                 "items": {"type": "string"},
            #                 "description": "Optional tags to filter by",
            #             },
            #         },
            #         "required": ["query"],
            #     },
            # ),
            # types.Tool(
            #     name="notes_ai_search",
            #     description=NOTES_AI_SEARCH_DESCRIPTION,
            #     inputSchema={
            #         "type": "object",
            #         "properties": {
            #             "query": {
            #                 "type": "string",
            #                 "description": "Search query for semantic search",
            #             },
            #             "tags": {
            #                 "type": "array",
            #                 "items": {"type": "string"},
            #                 "description": "Optional tags to filter by",
            #             },
            #         },
            #         "required": ["query"],
            #     },
            # ),
            # Curl tool
            types.Tool(
                name="curl",
                description=CURL_DESCRIPTION,
                inputSchema={
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Full curl command (e.g., 'curl -s -X GET http://localhost:7700/health')",
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds (default 30)",
                        },
                    },
                    "required": ["command"],
                },
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
            return await _handle_run_command(arguments)

        if name == "list_pal_commands":
            return _handle_list_commands()

        if name == "read_pal_resource":
            return await _handle_read_resource(arguments)

        if name == "list_pal_resources":
            return await _handle_list_resources()

        # Granular notes tools - DISABLED (using curl tool + instruction files instead)
        # if name == "notes_list":
        #     return _handle_notes_list(arguments)
        #
        # if name == "notes_add":
        #     return _handle_notes_add(arguments)
        #
        # if name == "notes_view":
        #     return _handle_notes_view(arguments)
        #
        # if name == "notes_delete":
        #     return _handle_notes_delete(arguments)
        #
        # if name == "notes_tags":
        #     return _handle_notes_tags(arguments)
        #
        # if name == "notes_search":
        #     return _handle_notes_search(arguments)
        #
        # if name == "notes_ai_search":
        #     return _handle_notes_ai_search(arguments)

        if name == "curl":
            return _handle_curl(arguments)

        raise ValueError(f"Unknown tool: {name}")

    @server.list_resources()  # type: ignore[misc]
    async def list_resources() -> list[types.Resource]:
        """List available prompt and instruction files as MCP resources."""
        resources: list[types.Resource] = []
        settings = get_settings()

        # List instruction files (hierarchical: git.md, git/commit.md, etc.)
        instructions_path = settings.instructions_path
        if instructions_path.exists():
            for path in instructions_path.rglob("*.md"):
                rel_path = path.relative_to(instructions_path)
                # Skip prompts subdirectory (handled separately)
                if rel_path.parts and rel_path.parts[0] == "prompts":
                    continue
                resources.append(
                    types.Resource(
                        uri=f"pal://instructions/{rel_path}",
                        name=str(rel_path),
                        description=f"Instruction file: {rel_path}",
                        mimeType="text/markdown",
                    )
                )

        # List custom prompts
        for name in list_custom_prompts():
            resources.append(
                types.Resource(
                    uri=f"pal://prompts/{name}.md",
                    name=f"{name}.md",
                    description=f"Custom prompt: {name}",
                    mimeType="text/markdown",
                )
            )

        return resources

    @server.read_resource()  # type: ignore[misc]
    async def read_resource(uri: types.AnyUrl) -> list[ReadResourceContents]:
        """Read a prompt or instruction file by URI.

        URI formats:
            pal://instructions/git.md
            pal://instructions/git/commit.md
            pal://prompts/tr.md
        """
        uri_str = str(uri)
        content: str | None = None

        if uri_str.startswith("pal://instructions/"):
            # Parse path: git.md -> namespace="git", subcommand=None
            #             git/commit.md -> namespace="git", subcommand="commit"
            rel_path = uri_str[len("pal://instructions/") :]
            parts = rel_path.removesuffix(".md").split("/")

            if len(parts) == 1:
                content = load_instruction(parts[0])
            elif len(parts) == 2:
                content = load_instruction(parts[0], parts[1])
            else:
                # Deeper nesting - read file directly
                settings = get_settings()
                file_path = settings.instructions_path / rel_path
                if file_path.exists():
                    content = file_path.read_text(encoding="utf-8")

        elif uri_str.startswith("pal://prompts/"):
            name = uri_str[len("pal://prompts/") :].removesuffix(".md")
            content = load_custom_prompt(name)

        if content is None:
            raise ValueError(f"Resource not found: {uri_str}")

        return [ReadResourceContents(content=content, mime_type="text/markdown")]


async def _handle_run_command(
    arguments: dict[str, str],
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle the run_pal_command tool.

    Args:
        arguments: The tool arguments containing the command.

    Returns:
        List of text content with the command results.
    """
    # Get request context for MCP session access (e.g., sampling)
    try:
        ctx = request_ctx.get()
    except LookupError:
        ctx = None

    command_string = arguments.get("command", "").strip()
    pipeline = parse_pipeline(command_string)

    if not pipeline:
        return [types.TextContent(type="text", text="Error: No command provided")]

    results: list[str] = []

    for raw_command in pipeline:
        parsed = parse_command(raw_command)
        output = await execute_command(parsed, ctx)
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


async def _handle_read_resource(
    arguments: dict[str, str],
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle the read_pal_resource tool.

    Args:
        arguments: The tool arguments containing the URI.

    Returns:
        List of text content with the resource content.
    """
    uri = arguments.get("uri", "").strip()
    if not uri:
        return [types.TextContent(type="text", text="Error: URI is required")]

    content: str | None = None

    if uri.startswith("pal://instructions/"):
        rel_path = uri[len("pal://instructions/") :]
        parts = rel_path.removesuffix(".md").split("/")

        if len(parts) == 1:
            content = load_instruction(parts[0])
            # load_instruction returns "Unknown command: ..." if not found
            if content.startswith("Unknown command:"):
                content = None
        elif len(parts) == 2:
            content = load_instruction(parts[0], parts[1])
            if content.startswith("Unknown command:"):
                content = None
        else:
            # Deeper nesting - read file directly
            settings = get_settings()
            file_path = settings.instructions_path / rel_path
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")

    elif uri.startswith("pal://prompts/"):
        name = uri[len("pal://prompts/") :].removesuffix(".md")
        content = load_custom_prompt(name)

    if content is None:
        return [types.TextContent(type="text", text=f"Error: Resource not found: {uri}")]

    return [types.TextContent(type="text", text=content)]


async def _handle_list_resources() -> (
    list[types.TextContent | types.ImageContent | types.EmbeddedResource]
):
    """Handle the list_pal_resources tool.

    Returns:
        List of text content with available resource URIs.
    """
    resources: list[str] = []
    settings = get_settings()

    # List instruction files
    instructions_path = settings.instructions_path
    if instructions_path.exists():
        for path in sorted(instructions_path.rglob("*.md")):
            rel_path = path.relative_to(instructions_path)
            if rel_path.parts and rel_path.parts[0] == "prompts":
                continue
            resources.append(f"pal://instructions/{rel_path}")

    # List custom prompts
    for name in list_custom_prompts():
        resources.append(f"pal://prompts/{name}.md")

    output = "Available resources:\n" + "\n".join(f"  - {r}" for r in resources)
    return [types.TextContent(type="text", text=output)]


# Granular notes handlers - DISABLED (using curl tool + instruction files instead)
# def _handle_notes_list(
#     arguments: dict[str, Any],
# ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
#     """Handle the notes_list tool."""
#     import json
#
#     tags = arguments.get("tags")
#     limit = arguments.get("limit", 10)
#     result = notes_list(tags=tags, limit=limit)
#     return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
#
#
# def _handle_notes_add(
#     arguments: dict[str, Any],
# ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
#     """Handle the notes_add tool."""
#     import json
#
#     content = arguments.get("content", "")
#     tags = arguments.get("tags")
#     result = notes_add(content=content, tags=tags)
#     return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
#
#
# def _handle_notes_view(
#     arguments: dict[str, Any],
# ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
#     """Handle the notes_view tool."""
#     import json
#
#     note_id = arguments.get("note_id", "")
#     result = notes_view(note_id=note_id)
#     return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
#
#
# def _handle_notes_delete(
#     arguments: dict[str, Any],
# ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
#     """Handle the notes_delete tool."""
#     import json
#
#     note_id = arguments.get("note_id", "")
#     result = notes_delete(note_id=note_id)
#     return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
#
#
# def _handle_notes_tags(
#     arguments: dict[str, Any],
# ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
#     """Handle the notes_tags tool."""
#     import json
#
#     note_id = arguments.get("note_id", "")
#     tags = arguments.get("tags", [])
#     result = notes_tags(note_id=note_id, tags=tags)
#     return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
#
#
# def _handle_notes_search(
#     arguments: dict[str, Any],
# ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
#     """Handle the notes_search tool."""
#     import json
#
#     query = arguments.get("query", "")
#     tags = arguments.get("tags")
#     result = notes_search(query=query, tags=tags)
#     return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
#
#
# def _handle_notes_ai_search(
#     arguments: dict[str, Any],
# ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
#     """Handle the notes_ai_search tool."""
#     import json
#
#     query = arguments.get("query", "")
#     tags = arguments.get("tags")
#     result = notes_ai_search(query=query, tags=tags)
#     return [types.TextContent(type="text", text=json.dumps(result, indent=2))]


def _handle_curl(
    arguments: dict[str, Any],
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle the curl tool."""
    import json

    command = arguments.get("command", "")
    timeout = arguments.get("timeout", 30)
    result = execute_curl(command=command, timeout=timeout)
    return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
