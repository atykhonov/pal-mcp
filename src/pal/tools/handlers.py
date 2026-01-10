"""Command handlers for built-in commands."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from pal.prompts import (
    get_prompt_path,
    list_builtin_prompts,
    list_custom_prompts,
    list_subcommands,
    load_custom_prompt,
    load_merged_prompt,
    load_prompt,
    parse_frontmatter,
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
    "prompt": "List, view, or create custom prompts",
    "help": "Show all available commands",
}



def handle_echo(
    command: ParsedCommand,
    ctx: RequestContext[ServerSession, object, object] | None = None,
) -> CommandResult | None:
    """Handle the echo command."""
    if command.namespace != "echo":
        return None
    return CommandResult(output=command.rest or "")


def handle_prompt(
    command: ParsedCommand,
    ctx: RequestContext[ServerSession, object, object] | None = None,
) -> CommandResult | None:
    """Handle the prompt command for managing custom prompts.

    Usage:
        $$prompt                         - List all custom prompts
        $$prompt name                    - View prompt definition
        $$prompt name -- content         - Create/update prompt with content

    Namespaced prompts create directory structure:
        $$prompt git add -- content      -> git/add.md
        $$prompt foo bar baz -- content  -> foo/bar/baz.md
    """
    if command.namespace != "prompt":
        return None

    # Parse using " -- " as delimiter between name and content
    if not command.rest:
        prompt_name = None
        prompt_content = None
    elif " -- " in command.rest:
        name_part, prompt_content = command.rest.split(" -- ", 1)
        prompt_name = name_part.strip() if name_part.strip() else None
    else:
        prompt_name = command.rest.strip() if command.rest.strip() else None
        prompt_content = None

    if not prompt_name:
        # List all custom prompts
        prompts = list_custom_prompts()
        if prompts:
            prompt_list = "\n".join(f"  - {p}" for p in prompts)
            content = f"Custom prompts:\n\n{prompt_list}"
        else:
            content = "No custom prompts defined yet."
        return CommandResult(output=f"## $$prompt\n\n{content}")

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
                f"$$prompt {prompt_name} -- Your instruction here\n\n"
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
    """Handle the $$help command to show all available prompts and commands."""
    if command.namespace != "help":
        return None

    lines: list[str] = ["## $$help", ""]

    lines.append("Use `$$` to run commands (e.g., `$$notes list`).")
    lines.append("In pipes, only the first command needs `$$`.")
    lines.append("")

    # Section 1: Built-in commands (Python handlers)
    lines.append("### Built-in Commands")
    lines.append("")
    for cmd, desc in sorted(BUILTIN_COMMANDS.items()):
        lines.append(f"- `{cmd}` - {desc}")
    lines.append("")

    # Section 2: Built-in prompts (bundled .md files)
    lines.append("### Built-in Prompts")
    lines.append("")
    for name, desc, _subcommands in list_builtin_prompts():
        lines.append(f"- `{name}` - {desc}")
    lines.append("")

    # Section 3: Custom prompts
    lines.append("### Custom Prompts")
    lines.append("")

    custom_prompts = list_custom_prompts()
    if custom_prompts:
        for prompt_name in custom_prompts:
            lines.append(f"- `{prompt_name}`")
    else:
        lines.append("No custom prompts defined yet.")
        lines.append("")
        lines.append("Create one with: `$$prompt <name> <instruction>`")

    return CommandResult(output="\n".join(lines))


def handle_help(
    command: ParsedCommand,
    ctx: RequestContext[ServerSession, object, object] | None = None,
) -> CommandResult | None:
    """Handle help requests for a namespace (e.g., $$git --help or $$git help)."""
    rest = command.rest.strip()
    first_word = rest.split()[0] if rest else ""
    is_help = first_word == "help" or rest.startswith("--help")

    if not is_help:
        return None

    subcommands = list_subcommands(command.namespace)

    if subcommands:
        cmd_list = "\n".join(f"  - {command.namespace} {sc}" for sc in subcommands)
        content = f"Available prompts:\n\n{cmd_list}"
    else:
        content = f"No subprompts available for '{command.namespace}'."

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


def load_prompt_chain(tokens: list[str]) -> tuple[list[tuple[str, str]], str]:
    """Load all prompts in the command chain using hybrid approach.

    For each token in the chain, loads and merges prompts from both
    bundled and custom paths, applying merge_strategy from frontmatter.

    Uses frontmatter-based parsing when `subcommands:` is defined,
    otherwise falls back to greedy file loading.

    Args:
        tokens: List of command tokens (e.g., ["notes", "add", "-t", "work"])

    Returns:
        Tuple of (list of (path, content) tuples, remaining user input)
    """
    prompts: list[tuple[str, str]] = []
    path_parts: list[str] = []
    remaining_tokens = tokens.copy()

    while remaining_tokens:
        token = remaining_tokens[0]

        # Build path parts for this level
        current_path_parts = path_parts + [token]

        # Load and merge from both bundled and custom paths
        content = load_merged_prompt(current_path_parts)

        if content is None:
            break  # No more prompts, rest is user input

        current_path = "/".join(current_path_parts)
        prompts.append((current_path, content))
        path_parts.append(token)
        remaining_tokens.pop(0)

        # Check frontmatter for subcommands
        frontmatter, _ = parse_frontmatter(content)
        if "subcommands" in frontmatter:
            # Frontmatter-based: only continue if next token is valid subcommand
            if not remaining_tokens:
                break
            valid_subs = frontmatter.get("subcommands", {})
            if not valid_subs or remaining_tokens[0] not in valid_subs:
                break  # Next token not a valid subcommand (or no subcommands allowed)
        # No subcommands in frontmatter: continue with greedy approach

    user_input = " ".join(remaining_tokens)
    return prompts, user_input


def handle_standard_prompt(
    command: ParsedCommand,
    ctx: RequestContext[ServerSession, object, object] | None = None,
) -> CommandResult:
    """Handle prompt-based commands - returns bundled prompts.

    Bundles root.md (protocol) + command prompts + user input for the LLM to interpret.
    """
    parts: list[str] = []

    # 1. Always include root.md (protocol)
    root_content = load_prompt("root")
    if not root_content.startswith("Unknown command"):
        parts.append(f"# PAL Protocol\n\n{root_content}")

    # 2. Build token list from parsed command
    tokens = [command.namespace]
    if command.rest:
        tokens.extend(command.rest.split())

    # 3. Load prompt chain
    prompts, user_input = load_prompt_chain(tokens)

    # 4. Check if command exists
    if not prompts:
        # No command found - return helpful error message
        error_msg = (
            f"## $${command.namespace}\n\n"
            f"**Error:** The `$${command.namespace}` command isn't defined.\n\n"
            f"To create it:\n"
            f"```\n"
            f"$$prompt {command.namespace} Your instruction here\n"
            f"```"
        )
        return CommandResult(output=error_msg)

    # 5. Add each prompt in the chain
    for i, (path, content) in enumerate(prompts):
        if i == 0:
            parts.append(f"# Command: {path}\n\n{content}")
        else:
            parts.append(f"# Subcommand: {path}\n\n{content}")

    # 6. Include user input if any
    if user_input:
        parts.append(f"# User Input\n\n{user_input}")

    # 7. Build header for display
    header = f"## $${command.namespace}"
    if command.rest:
        header += f" {command.rest}"

    bundled = "\n\n---\n\n".join(parts)
    return CommandResult(output=f"{header}\n\n{bundled}")


# Ordered list of handlers to try
# Notes commands are handled via prompt files + curl tool (not hardcoded handlers)
# All prompt-based commands (bundled and custom) are handled by handle_standard_prompt
COMMAND_HANDLERS: list[CommandHandler] = [
    handle_echo,
    handle_prompt,
    handle_help_command,
    handle_help,
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

    # Fallback to standard prompt
    fallback_result = handle_standard_prompt(command, ctx)
    return fallback_result.output
