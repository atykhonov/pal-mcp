"""Command parsing utilities."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParsedCommand:
    """A parsed command with namespace, subcommand, and remaining text."""

    namespace: str
    subcommand: str | None
    rest: str

    def __bool__(self) -> bool:
        """Return True if namespace is non-empty."""
        return bool(self.namespace)


# Namespaces that support subcommands
NAMESPACES_WITH_SUBCOMMANDS: frozenset[str] = frozenset({"git", "prompt"})


def parse_pipeline(command_string: str) -> list[str]:
    """Parse a command string into a pipeline of commands.

    Args:
        command_string: The raw command (e.g., "git commit | review")

    Returns:
        List of raw command strings.

    Examples:
        >>> parse_pipeline("git commit | review")
        ['git commit', 'review']
        >>> parse_pipeline("")
        []
        >>> parse_pipeline("single command")
        ['single command']
    """
    if not command_string:
        return []

    segments = command_string.split("|")
    return [segment.strip() for segment in segments if segment.strip()]


def parse_command(raw_command: str) -> ParsedCommand:
    """Parse a raw command into namespace, subcommand, and remaining text.

    Args:
        raw_command: The raw command string (e.g., "git commit -m message")

    Returns:
        ParsedCommand with namespace, subcommand (if applicable), and rest.

    Examples:
        >>> parse_command("git commit -m msg")
        ParsedCommand(namespace='git', subcommand='commit', rest='-m msg')
        >>> parse_command("git --help")
        ParsedCommand(namespace='git', subcommand=None, rest='--help')
        >>> parse_command("tr Hello world")
        ParsedCommand(namespace='tr', subcommand=None, rest='Hello world')
        >>> parse_command("help")
        ParsedCommand(namespace='help', subcommand=None, rest='')
    """
    if not raw_command:
        return ParsedCommand(namespace="", subcommand=None, rest="")

    parts = raw_command.split(None, 1)  # Split on first whitespace
    namespace = parts[0].lower()

    if len(parts) == 1:
        return ParsedCommand(namespace=namespace, subcommand=None, rest="")

    rest = parts[1]

    # Check if next word is a subcommand (not a flag)
    next_parts = rest.split(None, 1)
    if next_parts and not next_parts[0].startswith("-"):
        potential_subcommand = next_parts[0].lower()

        # For certain namespaces, treat second word as subcommand
        if namespace in NAMESPACES_WITH_SUBCOMMANDS:
            remaining = next_parts[1] if len(next_parts) > 1 else ""
            return ParsedCommand(
                namespace=namespace,
                subcommand=potential_subcommand,
                rest=remaining,
            )

    # Everything else: no subcommand, rest is the input
    return ParsedCommand(namespace=namespace, subcommand=None, rest=rest)
