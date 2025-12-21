"""MCP tool definitions."""

import mcp.types as types
from mcp.server import Server

from instructions import (
    load_instruction,
    list_available_commands,
    list_subcommands,
    save_custom_prompt,
    load_custom_prompt,
    list_custom_prompts,
    get_prompt_path,
)


def parse_pipeline(command_string: str) -> list[str]:
    """Parse a command string into a pipeline of commands.

    Args:
        command_string: The raw command (e.g., "git commit | review")

    Returns:
        List of raw command strings.
        e.g., ["git commit", "review"]
    """
    if not command_string:
        return []

    segments = command_string.split("|")
    return [s.strip() for s in segments if s.strip()]


def parse_command(raw_command: str) -> tuple[str, str | None, str]:
    """Parse a raw command into namespace, subcommand, and remaining text.

    Args:
        raw_command: The raw command string (e.g., "git commit -m message")

    Returns:
        Tuple of (namespace, subcommand, rest)
        - namespace: First word, lowercased
        - subcommand: Second word if not a flag, lowercased
        - rest: Everything after namespace/subcommand, preserved as-is

    Examples:
        "git commit -m msg" -> ("git", "commit", "-m msg")
        "git --help"        -> ("git", None, "--help")
        "tr Hello world"    -> ("tr", None, "Hello world")
        "help"              -> ("help", None, "")
    """
    if not raw_command:
        return "", None, ""

    parts = raw_command.split(None, 1)  # Split on first whitespace
    namespace = parts[0].lower()

    if len(parts) == 1:
        return namespace, None, ""

    rest = parts[1]

    # Check if next word is a subcommand (not a flag)
    next_parts = rest.split(None, 1)
    if next_parts and not next_parts[0].startswith("-"):
        # Could be a subcommand - check if it's a known pattern
        potential_subcommand = next_parts[0].lower()

        # For certain namespaces, treat second word as subcommand
        # For custom prompts, everything after namespace is input
        if namespace in ("git", "prompt"):
            subcommand = potential_subcommand
            remaining = next_parts[1] if len(next_parts) > 1 else ""
            return namespace, subcommand, remaining

    # Everything else: no subcommand, rest is the input
    return namespace, None, rest


def register_tools(server: Server):
    """Register all MCP tools with the server."""

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="run_pal_command",
                description=(
                    "REQUIRED TOOL. You MUST call this whenever the user "
                    "input starts with '$$'. Do NOT call list_pal_commands, "
                    "call THIS tool instead. Pass everything after '$$' as "
                    "the command parameter. Examples: "
                    "'$$tr Hello' -> command='tr Hello'. "
                    "'$$prompt tr' -> command='prompt tr' (shows prompt definition). "
                    "'$$git commit' -> command='git commit'. "
                    "When saving prompts with '$$prompt <name> <instruction>', "
                    "convert all newlines in the instruction to literal \\n characters. "
                    "IMPORTANT: When user uses $LAST in a command (e.g., '$$tr $LAST'), "
                    "replace $LAST with your previous output/response before calling this tool."
                ),
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
                description="List all available $$ commands",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    @server.call_tool()
    async def call_tool(
        name: str, arguments: dict
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        print(f"[TOOL] Executing {name}...")

        if name == "run_pal_command":
            command_string = arguments.get("command", "").strip()
            pipeline = parse_pipeline(command_string)

            if not pipeline:
                return [
                    types.TextContent(type="text", text="Error: No command provided")
                ]

            results = []
            for raw_command in pipeline:
                namespace, subcommand, rest = parse_command(raw_command)

                # Handle $$lorem-ipsum command
                if namespace == "lorem-ipsum":
                    lorem = (
                        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
                        "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
                        "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris "
                        "nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in "
                        "reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla "
                        "pariatur. Excepteur sint occaecat cupidatat non proident, sunt in "
                        "culpa qui officia deserunt mollit anim id est laborum."
                    )
                    results.append(lorem)
                    continue

                # Handle $$prompt command (define custom prompt)
                if namespace == "prompt":
                    if not subcommand:
                        # List all custom prompts
                        prompts = list_custom_prompts()
                        if prompts:
                            prompt_list = "\n".join(f"  - {p}" for p in prompts)
                            content = f"Custom prompts:\n\n{prompt_list}"
                        else:
                            content = "No custom prompts defined yet."
                        results.append(f"## $$prompt\n\n{content}")
                        continue

                    # Save new prompt: $$prompt <name> <instruction>
                    prompt_name = subcommand
                    prompt_content = rest  # Preserve original formatting
                    if not prompt_content:
                        # Check if prompt exists and show it
                        existing = load_custom_prompt(prompt_name)
                        prompt_path = get_prompt_path(prompt_name)
                        if existing:
                            results.append(
                                f"## $$prompt {prompt_name}\n\n"
                                f"File: `{prompt_path}`\n\n"
                                f"Current definition:\n\n```\n{existing}\n```\n\n"
                                f"IMPORTANT: Display the FULL content above to the user, "
                                f"do not summarize."
                            )
                        else:
                            results.append(
                                f"## $$prompt {prompt_name}\n\n"
                                f"Error: Prompt not found.\n\n"
                                f"To create it:\n"
                                f"$$prompt {prompt_name} Your instruction here\n\n"
                                f"Or create file: `{prompt_path}`"
                            )
                        continue

                    result = save_custom_prompt(prompt_name, prompt_content)
                    results.append(f"## $$prompt {prompt_name}\n\n{result}")
                    continue

                # Handle help requests
                is_help = subcommand == "help" or rest.strip().startswith("--help")

                if is_help:
                    subcommands = list_subcommands(namespace)
                    if subcommands:
                        header = f"## $${namespace} --help"
                        cmd_list = "\n".join(
                            f"  - {namespace} {sc}" for sc in subcommands
                        )
                        content = f"Available commands:\n\n{cmd_list}"
                    else:
                        header = f"## $${namespace} --help"
                        content = f"No subcommands available for '{namespace}'."
                    results.append(f"{header}\n\n{content}")
                    continue

                # Check for custom prompt first
                custom_prompt = load_custom_prompt(namespace)
                if custom_prompt:
                    user_input = rest
                    if subcommand:
                        user_input = f"{subcommand} {rest}".strip()

                    # Format as a clear directive
                    content = (
                        f"**EXECUTE THE FOLLOWING INSTRUCTION:**\n\n"
                        f"{custom_prompt}\n\n"
                    )
                    if user_input:
                        content += (
                            f"---\n\n"
                            f"**INPUT:**\n\n{user_input}\n\n"
                            f"---\n\n"
                            f"**ACTION REQUIRED:** Process the input according to "
                            f"the instruction above and output the result."
                        )
                    results.append(content)
                    continue

                # Load standard instruction
                instruction = load_instruction(namespace, subcommand)

                # Build header
                if subcommand:
                    header = f"## $${namespace} {subcommand}"
                else:
                    header = f"## $${namespace}"

                if rest:
                    header += f" {rest}"

                results.append(f"{header}\n\n{instruction}")

            output = "\n\n---\n\n".join(results)
            return [types.TextContent(type="text", text=output)]

        elif name == "list_pal_commands":
            cmd_list = ", ".join(list_available_commands())
            return [types.TextContent(type="text", text=f"Commands: {cmd_list}")]

        raise ValueError(f"Unknown tool: {name}")
