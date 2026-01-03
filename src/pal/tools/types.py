"""Type definitions for command handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from pal.tools.parser import ParsedCommand


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Result of a command execution.

    Attributes:
        output: Full content that goes to the LLM context.
        display: Optional minimal text shown to user. If None, output is displayed.
        handled: Whether the command was handled.
    """

    output: str
    display: str | None = None
    handled: bool = True


class CommandHandler(Protocol):
    """Protocol for command handlers."""

    def __call__(self, command: ParsedCommand) -> CommandResult | None:
        """Handle a command and return the result, or None if not handled."""
        ...
