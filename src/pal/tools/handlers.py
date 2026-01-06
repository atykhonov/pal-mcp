"""Command handlers for built-in commands."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from pal.instructions import (
    get_prompt_path,
    list_custom_prompts,
    list_subcommands,
    load_custom_prompt,
    load_instruction,
    save_custom_prompt,
)
from pal.tools.parser import ParsedCommand
from pal.tools.types import CommandHandler, CommandResult

if TYPE_CHECKING:
    from mcp.server.session import ServerSession
    from mcp.shared.context import RequestContext

# Built-in commands with descriptions
# These are hardcoded handlers, not loaded from files
BUILTIN_COMMANDS: dict[str, str] = {
    "echo": "Echo text with variable substitution",
    "lorem-ipsum": "Generate Lorem ipsum placeholder text",
    "prompt": "List, view, or create custom prompts",
    "help": "Show all available commands",
}

# Notes commands are handled via instruction files + curl tool
# They appear in help via DEFAULT_INSTRUCTIONS["notes"]

# Default commands from DEFAULT_INSTRUCTIONS (loaded from files/defaults)
DEFAULT_COMMANDS: dict[str, str] = {
    "git commit": "Create a git commit with conventional format",
}

# Lorem ipsum text for the lorem-ipsum command
LOREM_IPSUM: str = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
    "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
    "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris "
    "nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in "
    "reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla "
    "pariatur. Excepteur sint occaecat cupidatat non proident, sunt in "
    "culpa qui officia deserunt mollit anim id est laborum."
)


def handle_echo(
    command: ParsedCommand,
    ctx: RequestContext[ServerSession, object, object] | None = None,
) -> CommandResult | None:
    """Handle the echo command."""
    if command.namespace != "echo":
        return None
    return CommandResult(output=command.rest or "")


def handle_lorem_ipsum(
    command: ParsedCommand,
    ctx: RequestContext[ServerSession, object, object] | None = None,
) -> CommandResult | None:
    """Handle the lorem-ipsum command."""
    if command.namespace != "lorem-ipsum":
        return None
    return CommandResult(output=LOREM_IPSUM)


def handle_prompt(
    command: ParsedCommand,
    ctx: RequestContext[ServerSession, object, object] | None = None,
) -> CommandResult | None:
    """Handle the prompt command for managing custom prompts."""
    if command.namespace != "prompt":
        return None

    if not command.subcommand:
        # List all custom prompts
        prompts = list_custom_prompts()
        if prompts:
            prompt_list = "\n".join(f"  - {p}" for p in prompts)
            content = f"Custom prompts:\n\n{prompt_list}"
        else:
            content = "No custom prompts defined yet."
        return CommandResult(output=f"## $$prompt\n\n{content}")

    prompt_name = command.subcommand
    prompt_content = command.rest

    if not prompt_content:
        # Check if prompt exists and show it
        existing = load_custom_prompt(prompt_name)
        prompt_path = get_prompt_path(prompt_name)

        if existing:
            output = (
                f"## $$prompt {prompt_name}\n\n"
                f"File: `{prompt_path}`\n\n"
                f"Current definition:\n\n```\n{existing}\n```\n\n"
                f"IMPORTANT: Display the FULL content above to the user, "
                f"do not summarize."
            )
        else:
            output = (
                f"## $$prompt {prompt_name}\n\n"
                f"Error: Prompt not found.\n\n"
                f"To create it:\n"
                f"$$prompt {prompt_name} Your instruction here\n\n"
                f"Or create file: `{prompt_path}`"
            )
        return CommandResult(output=output)

    # Save new prompt
    result = save_custom_prompt(prompt_name, prompt_content)
    return CommandResult(output=f"## $$prompt {prompt_name}\n\n{result}")


def handle_help_command(
    command: ParsedCommand,
    ctx: RequestContext[ServerSession, object, object] | None = None,
) -> CommandResult | None:
    """Handle the $$help command to show all available commands."""
    if command.namespace != "help":
        return None

    lines: list[str] = ["## $$help", ""]

    # Section 1: Pre-defined commands
    lines.append("### Pre-defined Commands")
    lines.append("")

    # Built-in handlers
    for cmd, desc in sorted(BUILTIN_COMMANDS.items()):
        lines.append(f"- `$${cmd}` - {desc}")

    # Default commands from DEFAULT_INSTRUCTIONS
    for cmd, desc in sorted(DEFAULT_COMMANDS.items()):
        lines.append(f"- `$${cmd}` - {desc}")

    # Notes commands (available via instruction files + curl)
    lines.append(f"- `$$notes` - Manage notes (list, add, search, ai)")

    lines.append("")

    # Section 2: Custom commands
    lines.append("### Custom Commands")
    lines.append("")

    custom_prompts = list_custom_prompts()
    if custom_prompts:
        for prompt_name in custom_prompts:
            lines.append(f"- `$${prompt_name}`")
    else:
        lines.append("No custom commands defined yet.")
        lines.append("")
        lines.append("Create one with: `$$prompt <name> <instruction>`")

    return CommandResult(output="\n".join(lines))


def handle_help(
    command: ParsedCommand,
    ctx: RequestContext[ServerSession, object, object] | None = None,
) -> CommandResult | None:
    """Handle help requests for a namespace (e.g., $$git --help)."""
    is_help = command.subcommand == "help" or command.rest.strip().startswith("--help")

    if not is_help:
        return None

    subcommands = list_subcommands(command.namespace)

    if subcommands:
        cmd_list = "\n".join(f"  - {command.namespace} {sc}" for sc in subcommands)
        content = f"Available commands:\n\n{cmd_list}"
    else:
        content = f"No subcommands available for '{command.namespace}'."

    header = f"## $${command.namespace} --help"
    return CommandResult(output=f"{header}\n\n{content}")


def handle_custom_prompt(
    command: ParsedCommand,
    ctx: RequestContext[ServerSession, object, object] | None = None,
) -> CommandResult | None:
    """Handle custom prompt execution."""
    custom_prompt = load_custom_prompt(command.namespace)

    if not custom_prompt:
        return None

    user_input = command.rest
    if command.subcommand:
        user_input = f"{command.subcommand} {command.rest}".strip()

    content = f"**EXECUTE THE FOLLOWING INSTRUCTION:**\n\n{custom_prompt}\n\n"

    if user_input:
        content += (
            f"---\n\n"
            f"**INPUT:**\n\n{user_input}\n\n"
            f"---\n\n"
            f"**ACTION REQUIRED:** Process the input according to "
            f"the instruction above and output the result."
        )

    return CommandResult(output=content)


def handle_standard_instruction(
    command: ParsedCommand,
    ctx: RequestContext[ServerSession, object, object] | None = None,
) -> CommandResult:
    """Handle standard instruction lookup (fallback handler)."""
    instruction = load_instruction(command.namespace, command.subcommand)

    if command.subcommand:
        header = f"## $${command.namespace} {command.subcommand}"
    else:
        header = f"## $${command.namespace}"

    if command.rest:
        header += f" {command.rest}"

    return CommandResult(output=f"{header}\n\n{instruction}")


# Ordered list of handlers to try
# Notes commands are handled via instruction files + curl tool (not hardcoded handlers)
COMMAND_HANDLERS: list[CommandHandler] = [
    handle_echo,
    handle_lorem_ipsum,
    handle_prompt,
    handle_help_command,
    handle_help,
    handle_custom_prompt,
]


async def execute_command(
    command: ParsedCommand,
    ctx: RequestContext[ServerSession, object, object] | None = None,
) -> str:
    """Execute a command through the handler chain.

    Args:
        command: The parsed command to execute.
        ctx: Optional MCP request context for session access.

    Returns:
        The command output.
    """
    for handler in COMMAND_HANDLERS:
        result = handler(command, ctx)
        # Handle async handlers
        if asyncio.iscoroutine(result):
            result = await result
        if result is not None:
            if result.display is not None:
                # Quiet mode: show minimal display, full content in context block
                return (
                    f"{result.display}\n\n"
                    f"<context>\n{result.output}\n</context>"
                )
            return result.output

    # Fallback to standard instruction
    fallback_result = handle_standard_instruction(command, ctx)
    return fallback_result.output
