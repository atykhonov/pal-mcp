"""Prompt loading and management."""

from __future__ import annotations

import re
from importlib import resources
from pathlib import Path
from typing import Literal

import yaml

from pal.config import get_settings
from pal.prompts.defaults import DEFAULT_FILES

# Merge strategies for user prompts
MergeStrategy = Literal["override", "append", "prepend"]


def get_bundled_prompts_path() -> Path:
    """Get the path to bundled prompts directory."""
    # Use importlib.resources to get the bundled prompts path
    # This works both in development and when installed as a package
    with resources.as_file(resources.files("pal.prompts") / "bundled") as path:
        return Path(path)


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: The markdown content with optional frontmatter

    Returns:
        Tuple of (frontmatter dict, content without frontmatter)
    """
    frontmatter_pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
    match = frontmatter_pattern.match(content)

    if match:
        try:
            frontmatter = yaml.safe_load(match.group(1)) or {}
            body = content[match.end() :]
            return frontmatter, body
        except yaml.YAMLError:
            return {}, content

    return {}, content


def get_merge_strategy(frontmatter: dict) -> MergeStrategy:
    """Extract merge strategy from frontmatter.

    Args:
        frontmatter: Parsed frontmatter dictionary

    Returns:
        The merge strategy (default: "override")
    """
    strategy = frontmatter.get("merge_strategy", "override")
    if strategy in ("override", "append", "prepend"):
        return strategy  # type: ignore[return-value]
    return "override"


def merge_prompts(user_content: str, bundled_content: str, strategy: MergeStrategy) -> str:
    """Merge user and bundled prompts according to strategy.

    Args:
        user_content: User's prompt content (without frontmatter)
        bundled_content: Bundled prompt content
        strategy: How to merge the prompts

    Returns:
        Merged content
    """
    if strategy == "override":
        return user_content
    elif strategy == "append":
        return f"{bundled_content}\n\n{user_content}"
    elif strategy == "prepend":
        return f"{user_content}\n\n{bundled_content}"
    return user_content


def load_bundled_prompt(namespace: str, subcommand: str | None = None) -> str | None:
    """Load a prompt from bundled prompts.

    Args:
        namespace: The command namespace (e.g., "git")
        subcommand: The subcommand (e.g., "commit") or None

    Returns:
        The prompt content or None if not found
    """
    bundled_path = get_bundled_prompts_path()

    if subcommand:
        file_path = bundled_path / namespace / f"{subcommand}.md"
    else:
        file_path = bundled_path / f"{namespace}.md"

    if file_path.exists():
        return file_path.read_text(encoding="utf-8")

    return None


def load_user_prompt(namespace: str, subcommand: str | None = None) -> tuple[str | None, dict]:
    """Load a prompt from user prompts directory.

    Args:
        namespace: The command namespace (e.g., "git")
        subcommand: The subcommand (e.g., "commit") or None

    Returns:
        Tuple of (prompt content without frontmatter, frontmatter dict) or (None, {})
    """
    settings = get_settings()
    user_path = settings.prompts_path

    if subcommand:
        file_path = user_path / namespace / f"{subcommand}.md"
    else:
        file_path = user_path / f"{namespace}.md"

    if file_path.exists():
        content = file_path.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(content)
        return body, frontmatter

    return None, {}


def ensure_defaults() -> None:
    """Create default file templates if they don't exist."""
    settings = get_settings()
    settings.ensure_directories()

    files_path = settings.files_path

    for name, content in DEFAULT_FILES.items():
        file_path = files_path / name
        if not file_path.exists():
            file_path.write_text(content)


def load_prompt(namespace: str, subcommand: str | None = None) -> str:
    """Load prompt content for a command.

    Priority:
    1. User prompt (with merge strategy support)
    2. Bundled prompt
    3. Error message

    Args:
        namespace: The command namespace (e.g., "git") or flat command (e.g., "help")
        subcommand: The subcommand (e.g., "commit") or None for flat commands

    Returns:
        The prompt content or an error message if not found.
    """
    # Load user prompt if exists
    user_content, frontmatter = load_user_prompt(namespace, subcommand)

    # Load bundled prompt
    bundled_content = load_bundled_prompt(namespace, subcommand)

    if user_content is not None:
        if bundled_content is not None:
            # User prompt exists and bundled exists - apply merge strategy
            strategy = get_merge_strategy(frontmatter)
            return merge_prompts(user_content, bundled_content, strategy)
        else:
            # Only user prompt exists
            return user_content

    if bundled_content is not None:
        return bundled_content

    # Not found
    if subcommand:
        return f"Unknown command: {namespace} {subcommand}"
    return f"Unknown command: {namespace}"


# Built-in commands that are hardcoded handlers (not loaded from files)
BUILTIN_COMMANDS: set[str] = {"echo", "prompt", "help"}


def list_available_commands() -> list[str]:
    """List all available commands.

    Returns:
        Sorted list of command names (including namespaced commands).
    """
    settings = get_settings()
    user_path = settings.prompts_path
    bundled_path = get_bundled_prompts_path()

    commands: set[str] = set()

    # Add built-in commands (hardcoded handlers)
    commands.update(BUILTIN_COMMANDS)

    # Scan bundled prompts
    if bundled_path.exists():
        # Flat commands (*.md in root)
        for file_path in bundled_path.glob("*.md"):
            commands.add(file_path.stem)

        # Nested commands (namespace/subcommand.md)
        for directory in bundled_path.iterdir():
            if directory.is_dir():
                for file_path in directory.glob("*.md"):
                    commands.add(f"{directory.name} {file_path.stem}")

    # Scan user prompts (may add new commands or override)
    if user_path.exists():
        # Flat commands
        for file_path in user_path.glob("*.md"):
            commands.add(file_path.stem)

        # Nested commands
        for directory in user_path.iterdir():
            if directory.is_dir() and directory.name not in ("custom", "files"):
                for file_path in directory.glob("*.md"):
                    commands.add(f"{directory.name} {file_path.stem}")

    # Add custom prompts (including nested ones like "git add")
    custom_path = settings.custom_prompts_path
    if custom_path.exists():
        for file_path in custom_path.rglob("*.md"):
            commands.add(_path_to_name(custom_path, file_path))

    return sorted(commands)


def list_subcommands(namespace: str) -> list[str]:
    """List all available subcommands for a namespace.

    Args:
        namespace: The command namespace (e.g., "git")

    Returns:
        Sorted list of subcommand names.
    """
    settings = get_settings()
    user_path = settings.prompts_path
    bundled_path = get_bundled_prompts_path()
    custom_path = settings.custom_prompts_path

    subcommands: set[str] = set()

    # Check bundled prompts
    bundled_ns_dir = bundled_path / namespace
    if bundled_ns_dir.is_dir():
        for file_path in bundled_ns_dir.glob("*.md"):
            subcommands.add(file_path.stem)

    # Check user prompts
    user_ns_dir = user_path / namespace
    if user_ns_dir.is_dir():
        for file_path in user_ns_dir.glob("*.md"):
            subcommands.add(file_path.stem)

    # Check custom prompts
    custom_ns_dir = custom_path / namespace
    if custom_ns_dir.is_dir():
        for file_path in custom_ns_dir.glob("*.md"):
            subcommands.add(file_path.stem)

    return sorted(subcommands)


def _name_to_path(base_path: Path, name: str) -> Path:
    """Convert a prompt name to a file path.

    Args:
        base_path: The base directory for prompts
        name: The prompt name (e.g., "tr", "git add", "foo bar baz")

    Returns:
        Path like base_path/tr.md, base_path/git/add.md, base_path/foo/bar/baz.md
    """
    parts = name.split()
    if len(parts) == 1:
        return base_path / f"{parts[0]}.md"
    else:
        # All but last become directories, last becomes filename
        return base_path / "/".join(parts[:-1]) / f"{parts[-1]}.md"


def _path_to_name(base_path: Path, file_path: Path) -> str:
    """Convert a file path back to a prompt name.

    Args:
        base_path: The base directory for prompts
        file_path: The full path to the .md file

    Returns:
        Name like "tr", "git add", "foo bar baz"
    """
    relative = file_path.relative_to(base_path)
    # Remove .md extension and convert path separators to spaces
    name_parts = list(relative.parts)
    name_parts[-1] = name_parts[-1].removesuffix(".md")
    return " ".join(name_parts)


def save_custom_prompt(name: str, content: str) -> str:
    """Save a custom prompt.

    Args:
        name: The prompt name (e.g., "tr", "git add", "foo bar baz")
        content: The prompt content (supports \\n for newlines)

    Returns:
        Success or error message.
    """
    if not name:
        return "Error: Prompt name is required"

    settings = get_settings()
    settings.ensure_directories()

    # Convert literal \n to actual newlines
    content = content.replace("\\n", "\n")

    file_path = _name_to_path(settings.custom_prompts_path, name)

    # Create parent directories if needed
    file_path.parent.mkdir(parents=True, exist_ok=True)

    file_path.write_text(content, encoding="utf-8")

    return f"Prompt '{name}' saved. Use it with: $${name} <input>"


def load_custom_prompt(name: str) -> str | None:
    """Load a custom prompt.

    Args:
        name: The prompt name (e.g., "tr", "git add")

    Returns:
        Prompt content or None if not found.
    """
    settings = get_settings()
    file_path = _name_to_path(settings.custom_prompts_path, name)

    if file_path.exists():
        return file_path.read_text(encoding="utf-8")

    return None


def _load_bundled_by_path(path_parts: list[str]) -> str | None:
    """Load a bundled prompt by path parts.

    Args:
        path_parts: List of path components (e.g., ["git", "add"])

    Returns:
        The prompt content or None if not found.
    """
    bundled_path = get_bundled_prompts_path()
    file_path = bundled_path / "/".join(path_parts[:-1]) / f"{path_parts[-1]}.md" if len(path_parts) > 1 else bundled_path / f"{path_parts[0]}.md"

    if file_path.exists():
        return file_path.read_text(encoding="utf-8")

    return None


def _load_custom_by_path(path_parts: list[str]) -> tuple[str | None, dict]:
    """Load a custom prompt by path parts.

    Args:
        path_parts: List of path components (e.g., ["git", "add"])

    Returns:
        Tuple of (prompt content without frontmatter, frontmatter dict) or (None, {})
    """
    settings = get_settings()
    custom_path = settings.custom_prompts_path

    if len(path_parts) > 1:
        file_path = custom_path / "/".join(path_parts[:-1]) / f"{path_parts[-1]}.md"
    else:
        file_path = custom_path / f"{path_parts[0]}.md"

    if file_path.exists():
        content = file_path.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(content)
        return body, frontmatter

    return None, {}


def load_merged_prompt(path_parts: list[str]) -> str | None:
    """Load and merge a prompt from bundled and custom paths.

    Applies merge_strategy from custom prompt's frontmatter:
    - "override" (default): custom replaces bundled
    - "append": bundled + custom
    - "prepend": custom + bundled

    Args:
        path_parts: List of path components (e.g., ["git"] or ["git", "add"])

    Returns:
        The merged prompt content or None if not found in either location.
    """
    bundled_content = _load_bundled_by_path(path_parts)
    custom_content, frontmatter = _load_custom_by_path(path_parts)

    if custom_content is not None:
        if bundled_content is not None:
            strategy = get_merge_strategy(frontmatter)
            return merge_prompts(custom_content, bundled_content, strategy)
        else:
            return custom_content

    if bundled_content is not None:
        return bundled_content

    return None


def get_prompt_path(name: str) -> Path:
    """Get the file path for a custom prompt.

    Args:
        name: The prompt name (e.g., "tr", "git add")

    Returns:
        Path to the prompt file.
    """
    settings = get_settings()
    return _name_to_path(settings.custom_prompts_path, name)


def list_custom_prompts() -> list[str]:
    """List all custom prompts, including nested ones.

    Returns:
        Sorted list of custom prompt names (e.g., ["git add", "tr", "foo bar baz"]).
    """
    settings = get_settings()
    custom_prompts_path = settings.custom_prompts_path

    if not custom_prompts_path.exists():
        return []

    # Recursively find all .md files
    prompts = []
    for file_path in custom_prompts_path.rglob("*.md"):
        prompts.append(_path_to_name(custom_prompts_path, file_path))

    return sorted(prompts)


def _extract_description(content: str) -> str:
    """Extract a short description from prompt content.

    Takes the first line/sentence, strips markdown formatting.

    Args:
        content: The prompt file content

    Returns:
        A short description string
    """
    # Skip frontmatter if present
    _, body = parse_frontmatter(content)

    # Get first non-empty line
    for line in body.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # Skip markdown headers
        if line.startswith("#"):
            line = line.lstrip("#").strip()
        # Take first sentence or first 80 chars
        if ". " in line:
            line = line.split(". ")[0] + "."
        if len(line) > 80:
            line = line[:77] + "..."
        return line

    return "No description"


# Internal bundled files that should not appear in help
_INTERNAL_PROMPTS = {"root", "help", "curl"}


def list_builtin_prompts() -> list[tuple[str, str, list[str]]]:
    """List all built-in prompts with descriptions and subcommands.

    Returns:
        List of tuples: (namespace, description, subcommands)
        For flat commands, subcommands will be an empty list.
    """
    bundled_path = get_bundled_prompts_path()

    if not bundled_path.exists():
        return []

    prompts: list[tuple[str, str, list[str]]] = []

    # Find all .md files and directories
    for item in sorted(bundled_path.iterdir()):
        if item.name.startswith("."):
            continue

        if item.is_file() and item.suffix == ".md":
            name = item.stem
            # Skip internal prompts
            if name in _INTERNAL_PROMPTS:
                continue

            # Check if there's a corresponding directory with subcommands
            subdir = bundled_path / name
            if subdir.is_dir():
                # This is a namespace with subcommands - will be handled when we see the dir
                continue

            # Flat command (no subcommands)
            content = item.read_text(encoding="utf-8")
            description = _extract_description(content)
            prompts.append((name, description, []))

        elif item.is_dir():
            name = item.name
            # Skip internal directories
            if name in _INTERNAL_PROMPTS:
                continue

            # Get subcommands from directory
            subcommands = sorted(
                f.stem for f in item.glob("*.md") if not f.name.startswith(".")
            )

            if not subcommands:
                continue  # Empty directory, skip

            # Get description from namespace.md if it exists
            namespace_file = bundled_path / f"{name}.md"
            if namespace_file.exists():
                content = namespace_file.read_text(encoding="utf-8")
                description = _extract_description(content)
            else:
                # Generate description from subcommands
                description = f"Commands: {', '.join(subcommands)}"

            prompts.append((name, description, subcommands))

    return prompts
