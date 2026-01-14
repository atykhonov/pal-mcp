"""Tests for command handlers."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

from pal.tools.handlers import (
    execute_command,
    handle_custom_prompt,
    handle_echo,
    handle_help,
    handle_prompt,
    handle_standard_prompt,
)
from pal.tools.parser import ParsedCommand


class TestHandleEcho:
    """Tests for handle_echo handler."""

    def test_handles_echo_command(self) -> None:
        """handle_echo handles echo namespace."""
        cmd = ParsedCommand(namespace="echo", rest="Hello World")
        result = handle_echo(cmd)
        assert result is not None
        assert result.output == "Hello World"

    def test_handles_empty_echo(self) -> None:
        """handle_echo handles empty echo."""
        cmd = ParsedCommand(namespace="echo", rest="")
        result = handle_echo(cmd)
        assert result is not None
        assert result.output == ""

    def test_ignores_other_commands(self) -> None:
        """handle_echo returns None for non-echo commands."""
        cmd = ParsedCommand(namespace="other", rest="test")
        result = handle_echo(cmd)
        assert result is None


class TestHandlePrompt:
    """Tests for handle_prompt handler.

    Note: handle_prompt now parses its arguments from rest.
    - $$prompt           -> list prompts (rest="")
    - $$prompt name      -> view prompt (rest="name")
    - $$prompt name text -> create prompt (rest="name text")
    """

    def test_lists_prompts_when_no_args(self) -> None:
        """handle_prompt lists prompts when no arguments given."""
        with patch(
            "pal.tools.handlers.list_custom_prompts", return_value=["test1", "test2"]
        ):
            cmd = ParsedCommand(namespace="prompt", rest="")
            result = handle_prompt(cmd)
            assert result is not None
            assert "test1" in result.output
            assert "test2" in result.output

    def test_shows_empty_message_when_no_prompts(self) -> None:
        """handle_prompt shows message when no prompts exist."""
        with patch("pal.tools.handlers.list_custom_prompts", return_value=[]):
            cmd = ParsedCommand(namespace="prompt", rest="")
            result = handle_prompt(cmd)
            assert result is not None
            assert "No custom prompts" in result.output

    def test_shows_existing_prompt(self) -> None:
        """handle_prompt shows existing prompt definition."""
        with (
            patch(
                "pal.tools.handlers.load_custom_prompt",
                return_value="Test instruction",
            ),
            patch("pal.tools.handlers.get_prompt_path", return_value="/path/to"),
        ):
            cmd = ParsedCommand(namespace="prompt", rest="mytest")
            result = handle_prompt(cmd)
            assert result is not None
            assert "Test instruction" in result.output

    def test_shows_error_for_nonexistent_prompt(self) -> None:
        """handle_prompt shows error for nonexistent prompt."""
        with (
            patch("pal.tools.handlers.load_custom_prompt", return_value=None),
            patch("pal.tools.handlers.load_merged_prompt", return_value=None),
            patch("pal.tools.handlers.get_prompt_path", return_value="/path/to"),
        ):
            cmd = ParsedCommand(namespace="prompt", rest="missing")
            result = handle_prompt(cmd)
            assert result is not None
            assert "Error" in result.output or "not found" in result.output.lower()

    def test_falls_back_to_bundled_prompt(self) -> None:
        """handle_prompt shows bundled prompt when no custom exists."""
        with (
            patch("pal.tools.handlers.load_custom_prompt", return_value=None),
            patch(
                "pal.tools.handlers.load_merged_prompt",
                return_value="Bundled git commit instructions",
            ),
            patch("pal.tools.handlers.get_prompt_path", return_value="/path/to"),
        ):
            cmd = ParsedCommand(namespace="prompt", rest="git commit")
            result = handle_prompt(cmd)
            assert result is not None
            assert "Bundled git commit instructions" in result.output
            assert "Built-in prompt" in result.output

    def test_saves_new_prompt(self) -> None:
        """handle_prompt saves new prompt."""
        with patch(
            "pal.tools.handlers.save_custom_prompt", return_value="Prompt saved"
        ):
            cmd = ParsedCommand(namespace="prompt", rest="new -- New instruction")
            result = handle_prompt(cmd)
            assert result is not None
            assert "saved" in result.output.lower()

    def test_ignores_other_commands(self) -> None:
        """handle_prompt returns None for other commands."""
        cmd = ParsedCommand(namespace="other", rest="")
        result = handle_prompt(cmd)
        assert result is None


class TestHandleHelp:
    """Tests for handle_help handler.

    Note: handle_help now checks for "help" or "--help" in rest.
    """

    def test_handles_help_in_rest(self) -> None:
        """handle_help handles 'help' in rest."""
        with patch(
            "pal.tools.handlers.list_subcommands", return_value=["commit", "push"]
        ):
            cmd = ParsedCommand(namespace="git", rest="help")
            result = handle_help(cmd)
            assert result is not None
            assert "commit" in result.output
            assert "push" in result.output

    def test_handles_help_flag(self) -> None:
        """handle_help handles --help flag."""
        with patch("pal.tools.handlers.list_subcommands", return_value=["commit"]):
            cmd = ParsedCommand(namespace="git", rest="--help")
            result = handle_help(cmd)
            assert result is not None
            assert "commit" in result.output

    def test_shows_no_subcommands_message(self) -> None:
        """handle_help shows message when no subcommands."""
        with patch("pal.tools.handlers.list_subcommands", return_value=[]):
            cmd = ParsedCommand(namespace="custom", rest="help")
            result = handle_help(cmd)
            assert result is not None
            assert "No subprompts" in result.output

    def test_ignores_non_help(self) -> None:
        """handle_help returns None for non-help commands."""
        cmd = ParsedCommand(namespace="git", rest="commit -m msg")
        result = handle_help(cmd)
        assert result is None


class TestHandleCustomPrompt:
    """Tests for handle_custom_prompt handler."""

    def test_executes_custom_prompt(self) -> None:
        """handle_custom_prompt executes custom prompt with input."""
        with patch(
            "pal.tools.handlers.load_custom_prompt", return_value="Translate this:"
        ):
            cmd = ParsedCommand(namespace="tr", rest="Hello")
            result = handle_custom_prompt(cmd)
            assert result is not None
            assert "Translate this:" in result.output
            assert "Hello" in result.output
            assert "EXECUTE" in result.output

    def test_handles_rest_as_input(self) -> None:
        """handle_custom_prompt uses rest as user input."""
        with patch("pal.tools.handlers.load_custom_prompt", return_value="Process:"):
            cmd = ParsedCommand(namespace="custom", rest="sub rest")
            result = handle_custom_prompt(cmd)
            assert result is not None
            assert "sub rest" in result.output

    def test_returns_none_for_unknown_prompt(self) -> None:
        """handle_custom_prompt returns None for unknown prompts."""
        with patch("pal.tools.handlers.load_custom_prompt", return_value=None):
            cmd = ParsedCommand(namespace="unknown", rest="")
            result = handle_custom_prompt(cmd)
            assert result is None


class TestHandleStandardPrompt:
    """Tests for handle_standard_prompt handler.

    Note: handle_standard_prompt now bundles root.md + command prompts.
    """

    def test_bundles_prompts(self) -> None:
        """handle_standard_prompt bundles root and command prompts."""

        def mock_load_prompt(ns: str, sub: str | None = None) -> str:
            return {
                ("root", None): "Protocol content",
            }.get((ns, sub), f"Unknown command: {ns}")

        def mock_load_merged(path_parts: list[str]) -> str | None:
            key = tuple(path_parts)
            return {
                ("test",): "Test content",
            }.get(key)

        with (
            patch("pal.tools.handlers.load_prompt", side_effect=mock_load_prompt),
            patch("pal.tools.handlers.load_merged_prompt", side_effect=mock_load_merged),
        ):
            cmd = ParsedCommand(namespace="test", rest="")
            result = handle_standard_prompt(cmd)
            assert "# PAL Protocol" in result.output
            assert "Protocol content" in result.output
            assert "# Command: test" in result.output
            assert "Test content" in result.output

    def test_includes_rest_in_header(self) -> None:
        """handle_standard_prompt includes rest in header."""

        def mock_load_prompt(ns: str, sub: str | None = None) -> str:
            return {
                ("root", None): "Protocol",
            }.get((ns, sub), f"Unknown command: {ns}")

        def mock_load_merged(path_parts: list[str]) -> str | None:
            key = tuple(path_parts)
            return {
                ("test",): "Content",
            }.get(key)

        with (
            patch("pal.tools.handlers.load_prompt", side_effect=mock_load_prompt),
            patch("pal.tools.handlers.load_merged_prompt", side_effect=mock_load_merged),
        ):
            cmd = ParsedCommand(namespace="test", rest="-v")
            result = handle_standard_prompt(cmd)
            assert "## $$test -v" in result.output

    def test_includes_user_input(self) -> None:
        """handle_standard_prompt includes user input section."""

        def mock_load_prompt(ns: str, sub: str | None = None) -> str:
            return {
                ("root", None): "Protocol",
            }.get((ns, sub), f"Unknown command: {ns}")

        def mock_load_merged(path_parts: list[str]) -> str | None:
            key = tuple(path_parts)
            return {
                ("notes",): "Notes command",
            }.get(key)

        with (
            patch("pal.tools.handlers.load_prompt", side_effect=mock_load_prompt),
            patch("pal.tools.handlers.load_merged_prompt", side_effect=mock_load_merged),
        ):
            cmd = ParsedCommand(namespace="notes", rest="add hello world")
            result = handle_standard_prompt(cmd)
            # Since "add" doesn't have a file, it becomes part of user input
            assert "# User Input" in result.output


class TestExecuteCommand:
    """Tests for execute_command function."""

    def test_executes_echo(self) -> None:
        """execute_command handles echo."""
        cmd = ParsedCommand(namespace="echo", rest="test")
        result = asyncio.run(execute_command(cmd))
        assert result == "test"

    def test_falls_back_to_standard_prompt(self) -> None:
        """execute_command falls back to standard prompt."""

        def mock_load_prompt(ns: str, sub: str | None = None) -> str:
            return {
                ("root", None): "Protocol",
            }.get((ns, sub), f"Unknown command: {ns}")

        def mock_load_merged(path_parts: list[str]) -> str | None:
            key = tuple(path_parts)
            return {
                ("unknown",): "Standard",
            }.get(key)

        with (
            patch("pal.tools.handlers.load_custom_prompt", return_value=None),
            patch("pal.tools.handlers.load_prompt", side_effect=mock_load_prompt),
            patch("pal.tools.handlers.load_merged_prompt", side_effect=mock_load_merged),
        ):
            cmd = ParsedCommand(namespace="unknown", rest="")
            result = asyncio.run(execute_command(cmd))
            assert "Standard" in result
