"""Command parsing utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParsedCommand:
    """A parsed command with namespace and remaining text.

    Note: Subcommand detection is now handled dynamically by the prompt bundling
    logic based on file existence and frontmatter. The parser only extracts the
    namespace (first token).
    """

    namespace: str
    rest: str

    def __bool__(self) -> bool:
        """Return True if namespace is non-empty."""
        return bool(self.namespace)


# Commands that consume all remaining text as content (no pipe splitting after them).
# Format: "namespace" for any subcommand, or "namespace subcommand" for specific ones.
CONTENT_CONSUMING_COMMANDS: frozenset[str] = frozenset({
    "notes add",
    "notes save",
})


def _is_content_consuming_command(command_string: str) -> bool:
    """Check if command starts with a content-consuming prefix.

    Content-consuming commands take all remaining text as content,
    so pipes should not be interpreted as pipeline separators.

    Args:
        command_string: The raw command string.

    Returns:
        True if this is a content-consuming command.
    """
    lower = command_string.lower()
    for prefix in CONTENT_CONSUMING_COMMANDS:
        # Check if command starts with the prefix followed by whitespace or end
        if lower.startswith(prefix) and (
            len(lower) == len(prefix) or lower[len(prefix)].isspace()
        ):
            return True
    return False


def parse_pipeline(command_string: str) -> list[str]:
    """Parse a command string into a pipeline of commands.

    Args:
        command_string: The raw command (e.g., "git commit | review")

    Returns:
        List of raw command strings.

    Examples:
        >>> parse_pipeline("git commit | review")  # space around pipe
        ['git commit', 'review']
        >>> parse_pipeline("")
        []
        >>> parse_pipeline("single command")
        ['single command']
    """
    if not command_string:
        return []

    stripped = command_string.strip()

    # Content-consuming commands don't split on pipes - all text is content
    if _is_content_consuming_command(stripped):
        return [stripped] if stripped else []

    # If string starts or ends with |, it's likely a markdown table - don't split
    if stripped.startswith("|") or stripped.endswith("|"):
        return [stripped] if stripped else []

    # Split on " | " only when surrounded by word characters (letters/digits)
    segments = re.split(r"(?<=\w) \| (?=\w)", command_string)
    return [segment.strip() for segment in segments if segment.strip()]


def parse_command(raw_command: str) -> ParsedCommand:
    """Parse a raw command into namespace and remaining text.

    Subcommand detection is handled dynamically by the prompt bundling logic.
    This parser only extracts the namespace (first token) and leaves the rest
    for handlers to process.

    Args:
        raw_command: The raw command string (e.g., "notes add hello")

    Returns:
        ParsedCommand with namespace and rest.

    Examples:
        >>> parse_command("notes add hello")
        ParsedCommand(namespace='notes', rest='add hello')
        >>> parse_command("git commit -m msg")
        ParsedCommand(namespace='git', rest='commit -m msg')
        >>> parse_command("help")
        ParsedCommand(namespace='help', rest='')
    """
    if not raw_command:
        return ParsedCommand(namespace="", rest="")

    parts = raw_command.split(None, 1)  # Split on first whitespace
    namespace = parts[0].lower()
    rest = parts[1] if len(parts) > 1 else ""

    return ParsedCommand(namespace=namespace, rest=rest)
