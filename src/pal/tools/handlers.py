"""Command handlers for built-in commands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from pal.instructions import (
    get_prompt_path,
    list_custom_prompts,
    list_subcommands,
    load_custom_prompt,
    load_instruction,
    save_custom_prompt,
)
from pal.tools.parser import ParsedCommand

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


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Result of a command execution."""

    output: str
    handled: bool = True


class CommandHandler(Protocol):
    """Protocol for command handlers."""

    def __call__(self, command: ParsedCommand) -> CommandResult | None:
        """Handle a command and return the result, or None if not handled."""
        ...


def handle_echo(command: ParsedCommand) -> CommandResult | None:
    """Handle the echo command."""
    if command.namespace != "echo":
        return None
    return CommandResult(output=command.rest or "")


def handle_lorem_ipsum(command: ParsedCommand) -> CommandResult | None:
    """Handle the lorem-ipsum command."""
    if command.namespace != "lorem-ipsum":
        return None
    return CommandResult(output=LOREM_IPSUM)


def handle_prompt(command: ParsedCommand) -> CommandResult | None:
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


def handle_help(command: ParsedCommand) -> CommandResult | None:
    """Handle help requests for a namespace."""
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


def handle_custom_prompt(command: ParsedCommand) -> CommandResult | None:
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


def handle_standard_instruction(command: ParsedCommand) -> CommandResult:
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
COMMAND_HANDLERS: list[CommandHandler] = [
    handle_echo,
    handle_lorem_ipsum,
    handle_prompt,
    handle_help,
    handle_custom_prompt,
]


def execute_command(command: ParsedCommand) -> str:
    """Execute a command through the handler chain.

    Args:
        command: The parsed command to execute.

    Returns:
        The command output.
    """
    for handler in COMMAND_HANDLERS:
        result = handler(command)
        if result is not None:
            return result.output

    # Fallback to standard instruction
    fallback_result = handle_standard_instruction(command)
    return fallback_result.output
