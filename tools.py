"""MCP tool definitions."""

import shlex

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


def parse_pipeline(command_string: str) -> list[list[str]]:
    """Parse a command string into a pipeline of commands.

    Args:
        command_string: The raw command (e.g., "git commit | review")

    Returns:
        List of commands, each command is a list of tokens.
        e.g., [["git", "commit"], ["review"]]
    """
    if not command_string:
        return []

    # Split by pipe
    pipe_segments = command_string.split("|")
    pipeline = []

    for segment in pipe_segments:
        segment = segment.strip()
        if not segment:
            continue

        try:
            tokens = shlex.split(segment)
        except ValueError:
            # Fallback for malformed quotes
            tokens = segment.split()

        if tokens:
            pipeline.append(tokens)

    return pipeline


def resolve_command(tokens: list[str]) -> tuple[str, str | None, list[str]]:
    """Resolve tokens into namespace, subcommand, and extra args.

    Args:
        tokens: List of tokens (e.g., ["git", "commit", "-m", "message"])

    Returns:
        Tuple of (namespace, subcommand, extra_args)

    Examples:
        ["git", "commit"] -> ("git", "commit", [])
        ["git", "--help"] -> ("git", None, ["--help"])
        ["git", "help"]   -> ("git", "help", [])
        ["help"]          -> ("help", None, [])
    """
    if not tokens:
        return "", None, []

    namespace = tokens[0].lower()

    if len(tokens) == 1:
        return namespace, None, []

    # Check if second token is a flag (starts with -)
    second = tokens[1]
    if second.startswith("-"):
        # It's a flag, not a subcommand
        return namespace, None, tokens[1:]

    subcommand = second.lower()
    extra_args = tokens[2:]

    return namespace, subcommand, extra_args


def register_tools(server: Server):
    """Register all MCP tools with the server."""

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="run_pal_command",
                description=(
                    "REQUIRED TOOL. You MUST call this whenever the user "
                    "input starts with '$$'. Supports pipelines with '|'. "
                    "Usage: $$<command> or $$<cmd1> | <cmd2>"
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
            for tokens in pipeline:
                namespace, subcommand, extra_args = resolve_command(tokens)

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
                    prompt_content = " ".join(extra_args) if extra_args else ""
                    if not prompt_content:
                        # Check if prompt exists and show it
                        existing = load_custom_prompt(prompt_name)
                        prompt_path = get_prompt_path(prompt_name)
                        if existing:
                            results.append(
                                f"## $$prompt {prompt_name}\n\n"
                                f"File: `{prompt_path}`\n\n"
                                f"Current definition:\n\n{existing}"
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
                is_help = subcommand == "help" or "--help" in extra_args

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
                    # Build input from subcommand + extra_args
                    input_parts = []
                    if subcommand:
                        input_parts.append(subcommand)
                    input_parts.extend(extra_args)
                    user_input = " ".join(input_parts)

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

                if extra_args:
                    header += f" {' '.join(extra_args)}"

                results.append(f"{header}\n\n{instruction}")

            output = "\n\n---\n\n".join(results)
            return [types.TextContent(type="text", text=output)]

        elif name == "list_pal_commands":
            cmd_list = ", ".join(list_available_commands())
            return [types.TextContent(type="text", text=f"Commands: {cmd_list}")]

        raise ValueError(f"Unknown tool: {name}")
