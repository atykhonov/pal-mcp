"""Tests for command parsing."""

from __future__ import annotations

import pytest

from pal.tools.parser import ParsedCommand, parse_command, parse_pipeline


class TestParsePipeline:
    """Tests for parse_pipeline function."""

    def test_empty_string(self) -> None:
        """Empty string returns empty list."""
        assert parse_pipeline("") == []

    def test_single_command(self) -> None:
        """Single command returns list with one item."""
        assert parse_pipeline("git commit") == ["git commit"]

    def test_multiple_commands(self) -> None:
        """Multiple commands are split by pipe."""
        result = parse_pipeline("git commit | review")
        assert result == ["git commit", "review"]

    def test_whitespace_handling(self) -> None:
        """Whitespace around pipes is trimmed."""
        result = parse_pipeline("  cmd1 | cmd2 | cmd3  ")
        assert result == ["cmd1", "cmd2", "cmd3"]

    def test_markdown_table_not_split(self) -> None:
        """Markdown tables (starting/ending with |) are not split."""
        result = parse_pipeline("| col1 | col2 |")
        assert result == ["| col1 | col2 |"]

    def test_markdown_table_row_not_split(self) -> None:
        """Markdown table rows with data are not split."""
        result = parse_pipeline("| 7a8bd1a1 | This is a test | tags |")
        assert result == ["| 7a8bd1a1 | This is a test | tags |"]

    def test_pipe_in_content_preserved(self) -> None:
        """Pipe characters without spaces are preserved."""
        result = parse_pipeline("echo hello|world")
        assert result == ["echo hello|world"]

    def test_notes_add_no_pipe_split(self) -> None:
        """notes add is content-consuming - pipes are part of content."""
        content = "notes add # Title\n\n| Code | Meaning |\n| 200 | OK |"
        result = parse_pipeline(content)
        assert result == [content]

    def test_notes_add_with_table_content(self) -> None:
        """notes add preserves markdown tables with multiple pipes."""
        content = "notes add Some text\n\nCode | Meaning | Description\n200 | OK | Success"
        result = parse_pipeline(content)
        assert result == [content]

    def test_notes_save_no_pipe_split(self) -> None:
        """notes save is content-consuming - pipes are part of content."""
        content = "notes save # Article with | pipes | everywhere"
        result = parse_pipeline(content)
        assert result == [content]

    def test_regular_pipeline_still_works(self) -> None:
        """Regular commands still support pipeline."""
        result = parse_pipeline("git commit | review")
        assert result == ["git commit", "review"]

    def test_three_command_pipeline(self) -> None:
        """Three-command pipelines work for regular commands."""
        result = parse_pipeline("cmd1 | cmd2 | cmd3")
        assert result == ["cmd1", "cmd2", "cmd3"]


class TestParseCommand:
    """Tests for parse_command function."""

    def test_empty_string(self) -> None:
        """Empty string returns empty ParsedCommand."""
        result = parse_command("")
        assert result == ParsedCommand(namespace="", subcommand=None, rest="")
        assert not result  # bool is False for empty namespace

    def test_simple_command(self) -> None:
        """Simple command with no args."""
        result = parse_command("help")
        assert result == ParsedCommand(namespace="help", subcommand=None, rest="")

    def test_command_with_rest(self) -> None:
        """Command with rest text (no subcommand)."""
        result = parse_command("tr Hello world")
        assert result == ParsedCommand(
            namespace="tr", subcommand=None, rest="Hello world"
        )

    def test_git_with_subcommand(self) -> None:
        """Git namespace with subcommand."""
        result = parse_command("git commit -m message")
        assert result == ParsedCommand(
            namespace="git", subcommand="commit", rest="-m message"
        )

    def test_git_with_flag_no_subcommand(self) -> None:
        """Git with flag (starts with -) has no subcommand."""
        result = parse_command("git --help")
        assert result == ParsedCommand(namespace="git", subcommand=None, rest="--help")

    def test_prompt_with_subcommand(self) -> None:
        """Prompt namespace with subcommand."""
        result = parse_command("prompt myname instruction text")
        assert result == ParsedCommand(
            namespace="prompt", subcommand="myname", rest="instruction text"
        )

    def test_namespace_lowercased(self) -> None:
        """Namespace is lowercased."""
        result = parse_command("GIT commit")
        assert result.namespace == "git"

    def test_subcommand_lowercased(self) -> None:
        """Subcommand is lowercased."""
        result = parse_command("git COMMIT -m msg")
        assert result.subcommand == "commit"

    def test_rest_preserved(self) -> None:
        """Rest text preserves original case."""
        result = parse_command("tr Hello World")
        assert result.rest == "Hello World"

    def test_custom_command_no_subcommand(self) -> None:
        """Non-git/prompt commands don't parse subcommands."""
        result = parse_command("mycommand arg1 arg2")
        assert result == ParsedCommand(
            namespace="mycommand", subcommand=None, rest="arg1 arg2"
        )

    def test_bool_true_for_nonempty_namespace(self) -> None:
        """ParsedCommand is truthy when namespace is non-empty."""
        result = parse_command("cmd")
        assert result
        assert bool(result) is True


class TestParsedCommand:
    """Tests for ParsedCommand dataclass."""

    def test_frozen(self) -> None:
        """ParsedCommand is immutable."""
        cmd = ParsedCommand(namespace="test", subcommand=None, rest="")
        with pytest.raises(AttributeError):
            cmd.namespace = "other"  # type: ignore[misc]

    def test_equality(self) -> None:
        """ParsedCommand supports equality comparison."""
        cmd1 = ParsedCommand(namespace="test", subcommand="sub", rest="rest")
        cmd2 = ParsedCommand(namespace="test", subcommand="sub", rest="rest")
        assert cmd1 == cmd2

    def test_hash(self) -> None:
        """ParsedCommand is hashable."""
        cmd = ParsedCommand(namespace="test", subcommand="sub", rest="rest")
        assert hash(cmd) is not None
        # Can be used in sets
        cmd_set = {cmd}
        assert cmd in cmd_set
