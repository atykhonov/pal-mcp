"""Type definitions for command handlers."""

from __future__ import annotations

from collections.abc import Awaitable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from pal.tools.parser import ParsedCommand

if TYPE_CHECKING:
    from mcp.server.session import ServerSession
    from mcp.shared.context import RequestContext


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
    """Protocol for command handlers.

    Handlers can be sync or async, and optionally accept a RequestContext
    for MCP session access (e.g., for sampling).
    """

    def __call__(
        self,
        command: ParsedCommand,
        ctx: RequestContext[ServerSession, object, object] | None = None,
    ) -> CommandResult | Awaitable[CommandResult | None] | None:
        """Handle a command and return the result, or None if not handled."""
        ...
