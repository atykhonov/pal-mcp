"""Instruction loading and prompt management."""

from __future__ import annotations

from pathlib import Path

from pal.config import get_settings
from pal.instructions.defaults import DEFAULT_FILES, DEFAULT_INSTRUCTIONS


def ensure_defaults() -> None:
    """Create default instruction and file templates if they don't exist."""
    settings = get_settings()
    settings.ensure_directories()

    instructions_path = settings.instructions_path
    files_path = settings.files_path

    for name, content in DEFAULT_INSTRUCTIONS.items():
        if isinstance(content, dict):
            # Nested namespace (e.g., git/commit.md)
            namespace_dir = instructions_path / name
            namespace_dir.mkdir(parents=True, exist_ok=True)
            for subcommand, subcontent in content.items():
                file_path = namespace_dir / f"{subcommand}.md"
                if not file_path.exists():
                    file_path.write_text(subcontent)
        else:
            # Flat command (e.g., help.md)
            file_path = instructions_path / f"{name}.md"
            if not file_path.exists():
                file_path.write_text(content)

    for name, content in DEFAULT_FILES.items():
        file_path = files_path / name
        if not file_path.exists():
            file_path.write_text(content)


def load_instruction(namespace: str, subcommand: str | None = None) -> str:
    """Load instruction content for a command.

    Args:
        namespace: The command namespace (e.g., "git") or flat command (e.g., "help")
        subcommand: The subcommand (e.g., "commit") or None for flat commands

    Returns:
        The instruction content or an error message if not found.
    """
    settings = get_settings()
    instructions_path = settings.instructions_path

    if subcommand:
        # Nested: namespace/subcommand.md
        file_path = instructions_path / namespace / f"{subcommand}.md"
        if file_path.exists():
            return file_path.read_text(encoding="utf-8")

        # Check defaults
        ns_defaults = DEFAULT_INSTRUCTIONS.get(namespace)
        if isinstance(ns_defaults, dict) and subcommand in ns_defaults:
            return ns_defaults[subcommand]

        return f"Unknown command: {namespace} {subcommand}"

    # Flat: namespace.md
    file_path = instructions_path / f"{namespace}.md"
    if file_path.exists():
        return file_path.read_text(encoding="utf-8")

    content = DEFAULT_INSTRUCTIONS.get(namespace)
    if isinstance(content, str):
        return content

    return f"Unknown command: {namespace}"


# Built-in commands that are hardcoded handlers (not loaded from files)
BUILTIN_COMMANDS: set[str] = {"echo", "lorem-ipsum", "prompt", "help"}


def list_available_commands() -> list[str]:
    """List all available commands.

    Returns:
        Sorted list of command names (including namespaced commands).
    """
    settings = get_settings()
    instructions_path = settings.instructions_path
    prompts_path = settings.prompts_path

    commands: set[str] = set()

    # Add built-in commands (hardcoded handlers)
    commands.update(BUILTIN_COMMANDS)

    # Flat commands (*.md in root)
    for file_path in instructions_path.glob("*.md"):
        commands.add(file_path.stem)

    # Nested commands (namespace/subcommand.md), excluding "prompts" dir
    for directory in instructions_path.iterdir():
        if directory.is_dir() and directory.name != "prompts":
            for file_path in directory.glob("*.md"):
                commands.add(f"{directory.name} {file_path.stem}")

    # Add custom prompts as top-level commands
    if prompts_path.exists():
        for file_path in prompts_path.glob("*.md"):
            commands.add(file_path.stem)

    # Add defaults
    for name, content in DEFAULT_INSTRUCTIONS.items():
        if isinstance(content, dict):
            for subcommand in content:
                commands.add(f"{name} {subcommand}")
        else:
            commands.add(name)

    return sorted(commands)


def list_subcommands(namespace: str) -> list[str]:
    """List all available subcommands for a namespace.

    Args:
        namespace: The command namespace (e.g., "git")

    Returns:
        Sorted list of subcommand names.
    """
    settings = get_settings()
    instructions_path = settings.instructions_path

    subcommands: set[str] = set()

    # Check filesystem
    namespace_dir = instructions_path / namespace
    if namespace_dir.is_dir():
        for file_path in namespace_dir.glob("*.md"):
            subcommands.add(file_path.stem)

    # Check defaults
    ns_defaults = DEFAULT_INSTRUCTIONS.get(namespace)
    if isinstance(ns_defaults, dict):
        subcommands.update(ns_defaults.keys())

    return sorted(subcommands)


def save_custom_prompt(name: str, content: str) -> str:
    """Save a custom prompt.

    Args:
        name: The prompt name (e.g., "tr")
        content: The prompt instruction (supports \\n for newlines)

    Returns:
        Success or error message.
    """
    if not name:
        return "Error: Prompt name is required"

    settings = get_settings()
    settings.ensure_directories()

    # Convert literal \n to actual newlines
    content = content.replace("\\n", "\n")

    file_path = settings.prompts_path / f"{name}.md"
    file_path.write_text(content, encoding="utf-8")

    return f"Prompt '{name}' saved. Use it with: $${name} <input>"


def load_custom_prompt(name: str) -> str | None:
    """Load a custom prompt.

    Args:
        name: The prompt name

    Returns:
        Prompt content or None if not found.
    """
    settings = get_settings()
    file_path = settings.prompts_path / f"{name}.md"

    if file_path.exists():
        return file_path.read_text(encoding="utf-8")

    return None


def get_prompt_path(name: str) -> Path:
    """Get the file path for a prompt.

    Args:
        name: The prompt name

    Returns:
        Path to the prompt file.
    """
    settings = get_settings()
    return settings.prompts_path / f"{name}.md"


def list_custom_prompts() -> list[str]:
    """List all custom prompts.

    Returns:
        Sorted list of custom prompt names.
    """
    settings = get_settings()
    prompts_path = settings.prompts_path

    if not prompts_path.exists():
        return []

    return sorted(file_path.stem for file_path in prompts_path.glob("*.md"))
