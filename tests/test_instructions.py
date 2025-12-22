"""Tests for instruction loading and management."""

from __future__ import annotations

from unittest.mock import patch

from pal.config import Settings
from pal.instructions.defaults import DEFAULT_INSTRUCTIONS
from pal.instructions.loader import (
    ensure_defaults,
    list_available_commands,
    list_custom_prompts,
    list_subcommands,
    load_custom_prompt,
    load_instruction,
    save_custom_prompt,
)


class TestEnsureDefaults:
    """Tests for ensure_defaults function."""

    def test_creates_directories(self, test_settings: Settings) -> None:
        """ensure_defaults creates required directories."""
        with patch("pal.instructions.loader.get_settings", return_value=test_settings):
            ensure_defaults()

        assert test_settings.instructions_path.exists()
        assert test_settings.files_path.exists()

    def test_creates_default_instructions(self, test_settings: Settings) -> None:
        """ensure_defaults creates default instruction files."""
        with patch("pal.instructions.loader.get_settings", return_value=test_settings):
            ensure_defaults()

        # Check git/commit.md was created
        git_commit = test_settings.instructions_path / "git" / "commit.md"
        assert git_commit.exists()

        # Check help.md was created
        help_file = test_settings.instructions_path / "help.md"
        assert help_file.exists()

    def test_does_not_overwrite_existing(self, test_settings: Settings) -> None:
        """ensure_defaults doesn't overwrite existing files."""
        with patch("pal.instructions.loader.get_settings", return_value=test_settings):
            # Create directory and file first
            test_settings.instructions_path.mkdir(parents=True, exist_ok=True)
            help_file = test_settings.instructions_path / "help.md"
            help_file.write_text("custom content")

            ensure_defaults()

            # Should still have custom content
            assert help_file.read_text() == "custom content"


class TestLoadInstruction:
    """Tests for load_instruction function."""

    def test_loads_from_filesystem(self, test_settings: Settings) -> None:
        """load_instruction reads from filesystem."""
        with patch("pal.instructions.loader.get_settings", return_value=test_settings):
            test_settings.instructions_path.mkdir(parents=True, exist_ok=True)
            custom_file = test_settings.instructions_path / "custom.md"
            custom_file.write_text("custom instruction")

            result = load_instruction("custom")
            assert result == "custom instruction"

    def test_loads_nested_from_filesystem(self, test_settings: Settings) -> None:
        """load_instruction reads nested commands from filesystem."""
        with patch("pal.instructions.loader.get_settings", return_value=test_settings):
            ns_dir = test_settings.instructions_path / "myns"
            ns_dir.mkdir(parents=True, exist_ok=True)
            (ns_dir / "subcmd.md").write_text("nested instruction")

            result = load_instruction("myns", "subcmd")
            assert result == "nested instruction"

    def test_falls_back_to_defaults(self, test_settings: Settings) -> None:
        """load_instruction falls back to DEFAULT_INSTRUCTIONS."""
        with patch("pal.instructions.loader.get_settings", return_value=test_settings):
            test_settings.instructions_path.mkdir(parents=True, exist_ok=True)

            result = load_instruction("help")
            assert result == DEFAULT_INSTRUCTIONS["help"]

    def test_nested_falls_back_to_defaults(self, test_settings: Settings) -> None:
        """load_instruction falls back to nested defaults."""
        with patch("pal.instructions.loader.get_settings", return_value=test_settings):
            test_settings.instructions_path.mkdir(parents=True, exist_ok=True)

            result = load_instruction("git", "commit")
            git_defaults = DEFAULT_INSTRUCTIONS["git"]
            assert isinstance(git_defaults, dict)
            assert result == git_defaults["commit"]

    def test_unknown_command(self, test_settings: Settings) -> None:
        """load_instruction returns error for unknown commands."""
        with patch("pal.instructions.loader.get_settings", return_value=test_settings):
            test_settings.instructions_path.mkdir(parents=True, exist_ok=True)

            result = load_instruction("nonexistent")
            assert "Unknown command" in result

    def test_unknown_subcommand(self, test_settings: Settings) -> None:
        """load_instruction returns error for unknown subcommands."""
        with patch("pal.instructions.loader.get_settings", return_value=test_settings):
            test_settings.instructions_path.mkdir(parents=True, exist_ok=True)

            result = load_instruction("git", "nonexistent")
            assert "Unknown command" in result


class TestListAvailableCommands:
    """Tests for list_available_commands function."""

    def test_includes_defaults(self, test_settings: Settings) -> None:
        """list_available_commands includes default commands."""
        with patch("pal.instructions.loader.get_settings", return_value=test_settings):
            test_settings.instructions_path.mkdir(parents=True, exist_ok=True)
            test_settings.prompts_path.mkdir(parents=True, exist_ok=True)

            commands = list_available_commands()
            assert "help" in commands
            assert "git commit" in commands

    def test_includes_filesystem_commands(self, test_settings: Settings) -> None:
        """list_available_commands includes filesystem commands."""
        with patch("pal.instructions.loader.get_settings", return_value=test_settings):
            test_settings.instructions_path.mkdir(parents=True, exist_ok=True)
            test_settings.prompts_path.mkdir(parents=True, exist_ok=True)
            (test_settings.instructions_path / "custom.md").write_text("test")

            commands = list_available_commands()
            assert "custom" in commands

    def test_includes_custom_prompts(self, test_settings: Settings) -> None:
        """list_available_commands includes custom prompts."""
        with patch("pal.instructions.loader.get_settings", return_value=test_settings):
            test_settings.instructions_path.mkdir(parents=True, exist_ok=True)
            test_settings.prompts_path.mkdir(parents=True, exist_ok=True)
            (test_settings.prompts_path / "myprompt.md").write_text("test")

            commands = list_available_commands()
            assert "myprompt" in commands

    def test_returns_sorted_unique(self, test_settings: Settings) -> None:
        """list_available_commands returns sorted unique list."""
        with patch("pal.instructions.loader.get_settings", return_value=test_settings):
            test_settings.instructions_path.mkdir(parents=True, exist_ok=True)
            test_settings.prompts_path.mkdir(parents=True, exist_ok=True)

            commands = list_available_commands()
            assert commands == sorted(set(commands))


class TestListSubcommands:
    """Tests for list_subcommands function."""

    def test_returns_default_subcommands(self, test_settings: Settings) -> None:
        """list_subcommands returns subcommands from defaults."""
        with patch("pal.instructions.loader.get_settings", return_value=test_settings):
            test_settings.instructions_path.mkdir(parents=True, exist_ok=True)

            subcommands = list_subcommands("git")
            assert "commit" in subcommands

    def test_includes_filesystem_subcommands(self, test_settings: Settings) -> None:
        """list_subcommands includes subcommands from filesystem."""
        with patch("pal.instructions.loader.get_settings", return_value=test_settings):
            ns_dir = test_settings.instructions_path / "git"
            ns_dir.mkdir(parents=True, exist_ok=True)
            (ns_dir / "custom.md").write_text("test")

            subcommands = list_subcommands("git")
            assert "custom" in subcommands
            assert "commit" in subcommands

    def test_empty_for_unknown_namespace(self, test_settings: Settings) -> None:
        """list_subcommands returns empty for unknown namespace."""
        with patch("pal.instructions.loader.get_settings", return_value=test_settings):
            test_settings.instructions_path.mkdir(parents=True, exist_ok=True)

            subcommands = list_subcommands("unknown")
            assert subcommands == []


class TestCustomPrompts:
    """Tests for custom prompt functions."""

    def test_save_and_load_prompt(self, test_settings: Settings) -> None:
        """save_custom_prompt and load_custom_prompt work together."""
        with patch("pal.instructions.loader.get_settings", return_value=test_settings):
            result = save_custom_prompt("mytest", "Test instruction")
            assert "saved" in result.lower()

            loaded = load_custom_prompt("mytest")
            assert loaded == "Test instruction"

    def test_save_converts_newlines(self, test_settings: Settings) -> None:
        """save_custom_prompt converts literal \\n to newlines."""
        with patch("pal.instructions.loader.get_settings", return_value=test_settings):
            save_custom_prompt("newline", "Line 1\\nLine 2")

            loaded = load_custom_prompt("newline")
            assert loaded == "Line 1\nLine 2"

    def test_save_empty_name_error(self, test_settings: Settings) -> None:
        """save_custom_prompt returns error for empty name."""
        with patch("pal.instructions.loader.get_settings", return_value=test_settings):
            result = save_custom_prompt("", "content")
            assert "error" in result.lower()

    def test_load_nonexistent_returns_none(self, test_settings: Settings) -> None:
        """load_custom_prompt returns None for nonexistent prompt."""
        with patch("pal.instructions.loader.get_settings", return_value=test_settings):
            test_settings.prompts_path.mkdir(parents=True, exist_ok=True)

            result = load_custom_prompt("nonexistent")
            assert result is None

    def test_list_custom_prompts(self, test_settings: Settings) -> None:
        """list_custom_prompts returns sorted list of prompt names."""
        with patch("pal.instructions.loader.get_settings", return_value=test_settings):
            test_settings.prompts_path.mkdir(parents=True, exist_ok=True)
            (test_settings.prompts_path / "zebra.md").write_text("test")
            (test_settings.prompts_path / "alpha.md").write_text("test")

            prompts = list_custom_prompts()
            assert prompts == ["alpha", "zebra"]

    def test_list_custom_prompts_empty(self, test_settings: Settings) -> None:
        """list_custom_prompts returns empty list when no prompts."""
        with patch("pal.instructions.loader.get_settings", return_value=test_settings):
            # Don't create the directory
            prompts = list_custom_prompts()
            assert prompts == []
