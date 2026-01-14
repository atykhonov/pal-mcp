"""Command parsing utilities."""

from __future__ import annotations

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
