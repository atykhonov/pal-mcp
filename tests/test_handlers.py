"""Tests for command handlers."""

from __future__ import annotations

from unittest.mock import patch

from pal.tools.handlers import (
    LOREM_IPSUM,
    execute_command,
    handle_custom_prompt,
    handle_echo,
    handle_help,
    handle_lorem_ipsum,
    handle_prompt,
    handle_standard_instruction,
)
from pal.tools.parser import ParsedCommand


class TestHandleEcho:
    """Tests for handle_echo handler."""

    def test_handles_echo_command(self) -> None:
        """handle_echo handles echo namespace."""
        cmd = ParsedCommand(namespace="echo", subcommand=None, rest="Hello World")
        result = handle_echo(cmd)
        assert result is not None
        assert result.output == "Hello World"

    def test_handles_empty_echo(self) -> None:
        """handle_echo handles empty echo."""
        cmd = ParsedCommand(namespace="echo", subcommand=None, rest="")
        result = handle_echo(cmd)
        assert result is not None
        assert result.output == ""

    def test_ignores_other_commands(self) -> None:
        """handle_echo returns None for non-echo commands."""
        cmd = ParsedCommand(namespace="other", subcommand=None, rest="test")
        result = handle_echo(cmd)
        assert result is None


class TestHandleLoremIpsum:
    """Tests for handle_lorem_ipsum handler."""

    def test_handles_lorem_ipsum(self) -> None:
        """handle_lorem_ipsum returns lorem ipsum text."""
        cmd = ParsedCommand(namespace="lorem-ipsum", subcommand=None, rest="")
        result = handle_lorem_ipsum(cmd)
        assert result is not None
        assert result.output == LOREM_IPSUM

    def test_ignores_other_commands(self) -> None:
        """handle_lorem_ipsum returns None for other commands."""
        cmd = ParsedCommand(namespace="other", subcommand=None, rest="")
        result = handle_lorem_ipsum(cmd)
        assert result is None


class TestHandlePrompt:
    """Tests for handle_prompt handler."""

    def test_lists_prompts_when_no_subcommand(self) -> None:
        """handle_prompt lists prompts when no subcommand given."""
        with patch(
            "pal.tools.handlers.list_custom_prompts", return_value=["test1", "test2"]
        ):
            cmd = ParsedCommand(namespace="prompt", subcommand=None, rest="")
            result = handle_prompt(cmd)
            assert result is not None
            assert "test1" in result.output
            assert "test2" in result.output

    def test_shows_empty_message_when_no_prompts(self) -> None:
        """handle_prompt shows message when no prompts exist."""
        with patch("pal.tools.handlers.list_custom_prompts", return_value=[]):
            cmd = ParsedCommand(namespace="prompt", subcommand=None, rest="")
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
            cmd = ParsedCommand(namespace="prompt", subcommand="mytest", rest="")
            result = handle_prompt(cmd)
            assert result is not None
            assert "Test instruction" in result.output

    def test_shows_error_for_nonexistent_prompt(self) -> None:
        """handle_prompt shows error for nonexistent prompt."""
        with (
            patch("pal.tools.handlers.load_custom_prompt", return_value=None),
            patch("pal.tools.handlers.get_prompt_path", return_value="/path/to"),
        ):
            cmd = ParsedCommand(namespace="prompt", subcommand="missing", rest="")
            result = handle_prompt(cmd)
            assert result is not None
            assert "Error" in result.output or "not found" in result.output.lower()

    def test_saves_new_prompt(self) -> None:
        """handle_prompt saves new prompt."""
        with patch(
            "pal.tools.handlers.save_custom_prompt", return_value="Prompt saved"
        ):
            cmd = ParsedCommand(
                namespace="prompt", subcommand="new", rest="New instruction"
            )
            result = handle_prompt(cmd)
            assert result is not None
            assert "saved" in result.output.lower()

    def test_ignores_other_commands(self) -> None:
        """handle_prompt returns None for other commands."""
        cmd = ParsedCommand(namespace="other", subcommand=None, rest="")
        result = handle_prompt(cmd)
        assert result is None


class TestHandleHelp:
    """Tests for handle_help handler."""

    def test_handles_help_subcommand(self) -> None:
        """handle_help handles help subcommand."""
        with patch(
            "pal.tools.handlers.list_subcommands", return_value=["commit", "push"]
        ):
            cmd = ParsedCommand(namespace="git", subcommand="help", rest="")
            result = handle_help(cmd)
            assert result is not None
            assert "commit" in result.output
            assert "push" in result.output

    def test_handles_help_flag(self) -> None:
        """handle_help handles --help flag."""
        with patch("pal.tools.handlers.list_subcommands", return_value=["commit"]):
            cmd = ParsedCommand(namespace="git", subcommand=None, rest="--help")
            result = handle_help(cmd)
            assert result is not None
            assert "commit" in result.output

    def test_shows_no_subcommands_message(self) -> None:
        """handle_help shows message when no subcommands."""
        with patch("pal.tools.handlers.list_subcommands", return_value=[]):
            cmd = ParsedCommand(namespace="custom", subcommand="help", rest="")
            result = handle_help(cmd)
            assert result is not None
            assert "No subcommands" in result.output

    def test_ignores_non_help(self) -> None:
        """handle_help returns None for non-help commands."""
        cmd = ParsedCommand(namespace="git", subcommand="commit", rest="-m msg")
        result = handle_help(cmd)
        assert result is None


class TestHandleCustomPrompt:
    """Tests for handle_custom_prompt handler."""

    def test_executes_custom_prompt(self) -> None:
        """handle_custom_prompt executes custom prompt with input."""
        with patch(
            "pal.tools.handlers.load_custom_prompt", return_value="Translate this:"
        ):
            cmd = ParsedCommand(namespace="tr", subcommand=None, rest="Hello")
            result = handle_custom_prompt(cmd)
            assert result is not None
            assert "Translate this:" in result.output
            assert "Hello" in result.output
            assert "EXECUTE" in result.output

    def test_includes_subcommand_in_input(self) -> None:
        """handle_custom_prompt includes subcommand in user input."""
        with patch("pal.tools.handlers.load_custom_prompt", return_value="Process:"):
            cmd = ParsedCommand(namespace="custom", subcommand="sub", rest="rest")
            result = handle_custom_prompt(cmd)
            assert result is not None
            assert "sub rest" in result.output

    def test_returns_none_for_unknown_prompt(self) -> None:
        """handle_custom_prompt returns None for unknown prompts."""
        with patch("pal.tools.handlers.load_custom_prompt", return_value=None):
            cmd = ParsedCommand(namespace="unknown", subcommand=None, rest="")
            result = handle_custom_prompt(cmd)
            assert result is None


class TestHandleStandardInstruction:
    """Tests for handle_standard_instruction handler."""

    def test_loads_instruction(self) -> None:
        """handle_standard_instruction loads instruction."""
        with patch(
            "pal.tools.handlers.load_instruction", return_value="Instruction content"
        ):
            cmd = ParsedCommand(namespace="test", subcommand=None, rest="")
            result = handle_standard_instruction(cmd)
            assert result.output == "## $$test\n\nInstruction content"

    def test_includes_subcommand_in_header(self) -> None:
        """handle_standard_instruction includes subcommand in header."""
        with patch("pal.tools.handlers.load_instruction", return_value="Content"):
            cmd = ParsedCommand(namespace="git", subcommand="commit", rest="")
            result = handle_standard_instruction(cmd)
            assert "## $$git commit" in result.output

    def test_includes_rest_in_header(self) -> None:
        """handle_standard_instruction includes rest in header."""
        with patch("pal.tools.handlers.load_instruction", return_value="Content"):
            cmd = ParsedCommand(namespace="test", subcommand=None, rest="-v")
            result = handle_standard_instruction(cmd)
            assert "## $$test -v" in result.output


class TestExecuteCommand:
    """Tests for execute_command function."""

    def test_executes_echo(self) -> None:
        """execute_command handles echo."""
        cmd = ParsedCommand(namespace="echo", subcommand=None, rest="test")
        result = execute_command(cmd)
        assert result == "test"

    def test_executes_lorem_ipsum(self) -> None:
        """execute_command handles lorem-ipsum."""
        cmd = ParsedCommand(namespace="lorem-ipsum", subcommand=None, rest="")
        result = execute_command(cmd)
        assert result == LOREM_IPSUM

    def test_falls_back_to_standard_instruction(self) -> None:
        """execute_command falls back to standard instruction."""
        with (
            patch("pal.tools.handlers.load_custom_prompt", return_value=None),
            patch("pal.tools.handlers.load_instruction", return_value="Standard"),
        ):
            cmd = ParsedCommand(namespace="unknown", subcommand=None, rest="")
            result = execute_command(cmd)
            assert "Standard" in result
