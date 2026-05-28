"""Tests for command parsing."""

from __future__ import annotations

import pytest

from pal.tools.parser import ParsedCommand, parse_command


class TestParseCommand:
    """Tests for parse_command function.

    Note: Subcommand detection is now handled dynamically by the prompt bundling
    logic. The parser only extracts namespace (first token) and rest.
    """

    def test_empty_string(self) -> None:
        """Empty string returns empty ParsedCommand."""
        result = parse_command("")
        assert result == ParsedCommand(namespace="", rest="")
        assert not result  # bool is False for empty namespace

    def test_simple_command(self) -> None:
        """Simple command with no args."""
        result = parse_command("help")
        assert result == ParsedCommand(namespace="help", rest="")

    def test_command_with_rest(self) -> None:
        """Command with rest text."""
        result = parse_command("tr Hello world")
        assert result == ParsedCommand(namespace="tr", rest="Hello world")

    def test_git_command(self) -> None:
        """Git command - subcommand is now part of rest."""
        result = parse_command("git commit -m message")
        assert result == ParsedCommand(namespace="git", rest="commit -m message")

    def test_git_with_flag(self) -> None:
        """Git with flag."""
        result = parse_command("git --help")
        assert result == ParsedCommand(namespace="git", rest="--help")

    def test_prompt_command(self) -> None:
        """Prompt command - arguments are now part of rest."""
        result = parse_command("prompt myname instruction text")
        assert result == ParsedCommand(namespace="prompt", rest="myname instruction text")

    def test_namespace_lowercased(self) -> None:
        """Namespace is lowercased."""
        result = parse_command("GIT commit")
        assert result.namespace == "git"

    def test_rest_preserved(self) -> None:
        """Rest text preserves original case."""
        result = parse_command("tr Hello World")
        assert result.rest == "Hello World"

    def test_notes_command(self) -> None:
        """Notes command with subcommand and args."""
        result = parse_command("notes add -t work Meeting notes")
        assert result == ParsedCommand(namespace="notes", rest="add -t work Meeting notes")

    def test_bool_true_for_nonempty_namespace(self) -> None:
        """ParsedCommand is truthy when namespace is non-empty."""
        result = parse_command("cmd")
        assert result
        assert bool(result) is True

    def test_strips_leading_dollar_prefix(self) -> None:
        """Leading `$$` is stripped so callers can pass either form.

        The MCP `instructions` field is ambiguous about whether the LLM should
        pass `$$cmd` or `cmd` to run_pal_command; some sessions strip, some
        don't. Tolerating both keeps behavior uniform across clients.
        """
        result = parse_command("$$init-session")
        assert result == ParsedCommand(namespace="init-session", rest="")

    def test_strips_dollar_prefix_with_rest(self) -> None:
        """`$$cmd args` parses the same as `cmd args`."""
        result = parse_command("$$tr Hello world")
        assert result == ParsedCommand(namespace="tr", rest="Hello world")

    def test_strips_dollar_prefix_with_inner_whitespace(self) -> None:
        """Whitespace between `$$` and the command name is tolerated."""
        result = parse_command("$$ init-session")
        assert result == ParsedCommand(namespace="init-session", rest="")

    def test_only_dollar_prefix_yields_empty(self) -> None:
        """A bare `$$` (no command) produces an empty namespace, not `$$`."""
        result = parse_command("$$")
        assert result == ParsedCommand(namespace="", rest="")
        assert not result

    def test_strips_only_one_dollar_prefix(self) -> None:
        """`$$$$cmd` (double-prefixed input) collapses to `cmd`, not `$$cmd`.

        Guards against the `$$$$init-session` artifact that appeared when an
        already-prefixed input was wrapped again by the caller.
        """
        result = parse_command("$$$$init-session")
        assert result == ParsedCommand(namespace="init-session", rest="")


class TestParsedCommand:
    """Tests for ParsedCommand dataclass."""

    def test_frozen(self) -> None:
        """ParsedCommand is immutable."""
        cmd = ParsedCommand(namespace="test", rest="")
        with pytest.raises(AttributeError):
            cmd.namespace = "other"  # type: ignore[misc]

    def test_equality(self) -> None:
        """ParsedCommand supports equality comparison."""
        cmd1 = ParsedCommand(namespace="test", rest="sub rest")
        cmd2 = ParsedCommand(namespace="test", rest="sub rest")
        assert cmd1 == cmd2

    def test_hash(self) -> None:
        """ParsedCommand is hashable."""
        cmd = ParsedCommand(namespace="test", rest="sub rest")
        assert hash(cmd) is not None
        # Can be used in sets
        cmd_set = {cmd}
        assert cmd in cmd_set
