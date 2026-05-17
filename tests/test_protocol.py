"""Tests for the hoisted PAL protocol instructions constant."""

from __future__ import annotations

from pal.protocol import PROTOCOL_INSTRUCTIONS


def test_protocol_contains_builtin_command_names() -> None:
    """The protocol header must name every built-in command the LLM can invoke."""
    for name in ("$$echo", "$$prompt", "$$help"):
        assert name in PROTOCOL_INSTRUCTIONS, f"missing {name!r}"


def test_protocol_contains_variable_substitution_section() -> None:
    """The protocol header must document the $MSG / $REPLY variables."""
    assert "$MSG" in PROTOCOL_INSTRUCTIONS
    assert "`$REPLY` - Your previous response" in PROTOCOL_INSTRUCTIONS


def test_protocol_contains_executing_prompt_section() -> None:
    """The protocol header must explain how to interpret bundled prompts."""
    assert "Executing Prompt-Based Commands" in PROTOCOL_INSTRUCTIONS


def test_protocol_contains_error_handling_section() -> None:
    """The protocol header must keep the error-reporting guidance."""
    assert "Error Handling" in PROTOCOL_INSTRUCTIONS


def test_protocol_starts_with_pal_command_protocol_heading() -> None:
    """The protocol must begin with its canonical H1 heading."""
    assert PROTOCOL_INSTRUCTIONS.startswith("# PAL Command Protocol")
