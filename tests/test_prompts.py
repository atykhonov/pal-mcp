"""Tests for prompt loading and management."""

from __future__ import annotations

from unittest.mock import patch

from pal.config import Settings
from pal.prompts.loader import (
    ensure_defaults,
    get_bundled_prompts_path,
    get_merge_strategy,
    list_available_commands,
    list_custom_prompts,
    list_subcommands,
    load_bundled_prompt,
    load_custom_prompt,
    load_merged_prompt,
    load_prompt,
    merge_prompts,
    parse_frontmatter,
    save_custom_prompt,
)


class TestParseFrontmatter:
    """Tests for parse_frontmatter function."""

    def test_parses_yaml_frontmatter(self) -> None:
        """parse_frontmatter extracts YAML frontmatter."""
        content = """---
merge_strategy: append
key: value
---

# Body Content
"""
        frontmatter, body = parse_frontmatter(content)
        assert frontmatter["merge_strategy"] == "append"
        assert frontmatter["key"] == "value"
        assert "# Body Content" in body

    def test_no_frontmatter(self) -> None:
        """parse_frontmatter handles content without frontmatter."""
        content = "# Just content\nNo frontmatter here."
        frontmatter, body = parse_frontmatter(content)
        assert frontmatter == {}
        assert body == content

    def test_invalid_yaml(self) -> None:
        """parse_frontmatter handles invalid YAML gracefully."""
        content = """---
invalid: yaml: content:
---

Body
"""
        frontmatter, body = parse_frontmatter(content)
        assert frontmatter == {}
        assert body == content


class TestMergeStrategy:
    """Tests for merge strategy functions."""

    def test_get_merge_strategy_default(self) -> None:
        """get_merge_strategy returns 'override' by default."""
        assert get_merge_strategy({}) == "override"

    def test_get_merge_strategy_append(self) -> None:
        """get_merge_strategy returns 'append' when specified."""
        assert get_merge_strategy({"merge_strategy": "append"}) == "append"

    def test_get_merge_strategy_prepend(self) -> None:
        """get_merge_strategy returns 'prepend' when specified."""
        assert get_merge_strategy({"merge_strategy": "prepend"}) == "prepend"

    def test_get_merge_strategy_invalid(self) -> None:
        """get_merge_strategy returns 'override' for invalid values."""
        assert get_merge_strategy({"merge_strategy": "invalid"}) == "override"

    def test_merge_prompts_override(self) -> None:
        """merge_prompts with 'override' returns user content."""
        result = merge_prompts("user", "bundled", "override")
        assert result == "user"

    def test_merge_prompts_append(self) -> None:
        """merge_prompts with 'append' appends user to bundled."""
        result = merge_prompts("user", "bundled", "append")
        assert result == "bundled\n\nuser"

    def test_merge_prompts_prepend(self) -> None:
        """merge_prompts with 'prepend' prepends user to bundled."""
        result = merge_prompts("user", "bundled", "prepend")
        assert result == "user\n\nbundled"


class TestBundledPrompts:
    """Tests for bundled prompts loading."""

    def test_bundled_prompts_path_exists(self) -> None:
        """get_bundled_prompts_path returns existing path."""
        path = get_bundled_prompts_path()
        assert path.exists()

    def test_load_bundled_prompt_flat(self) -> None:
        """load_bundled_prompt loads flat commands."""
        result = load_bundled_prompt("help")
        assert result is not None
        assert "help" in result.lower() or "$$" in result

    def test_load_bundled_prompt_nested(self) -> None:
        """load_bundled_prompt loads nested commands."""
        result = load_bundled_prompt("git", "commit")
        assert result is not None
        assert "commit" in result.lower()

    def test_load_bundled_prompt_nonexistent(self) -> None:
        """load_bundled_prompt returns None for nonexistent."""
        result = load_bundled_prompt("nonexistent")
        assert result is None


class TestEnsureDefaults:
    """Tests for ensure_defaults function."""

    def test_creates_directories(self, test_settings: Settings) -> None:
        """ensure_defaults creates required directories."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            ensure_defaults()

        assert test_settings.prompts_path.exists()
        assert test_settings.files_path.exists()


class TestLoadPrompt:
    """Tests for load_prompt function."""

    def test_loads_from_user_filesystem(self, test_settings: Settings) -> None:
        """load_prompt reads from user filesystem."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            test_settings.prompts_path.mkdir(parents=True, exist_ok=True)
            custom_file = test_settings.prompts_path / "custom.md"
            custom_file.write_text("custom prompt")

            result = load_prompt("custom")
            assert result == "custom prompt"

    def test_loads_nested_from_user_filesystem(self, test_settings: Settings) -> None:
        """load_prompt reads nested commands from user filesystem."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            ns_dir = test_settings.prompts_path / "myns"
            ns_dir.mkdir(parents=True, exist_ok=True)
            (ns_dir / "subcmd.md").write_text("nested prompt")

            result = load_prompt("myns", "subcmd")
            assert result == "nested prompt"

    def test_falls_back_to_bundled(self, test_settings: Settings) -> None:
        """load_prompt falls back to bundled prompts."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            test_settings.prompts_path.mkdir(parents=True, exist_ok=True)

            result = load_prompt("help")
            # Should load from bundled
            assert "help" in result.lower() or "$$" in result

    def test_nested_falls_back_to_bundled(self, test_settings: Settings) -> None:
        """load_prompt falls back to bundled nested prompts."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            test_settings.prompts_path.mkdir(parents=True, exist_ok=True)

            result = load_prompt("git", "commit")
            assert "commit" in result.lower()

    def test_unknown_command(self, test_settings: Settings) -> None:
        """load_prompt returns error for unknown commands."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            test_settings.prompts_path.mkdir(parents=True, exist_ok=True)

            result = load_prompt("nonexistent")
            assert "Unknown command" in result

    def test_unknown_subcommand(self, test_settings: Settings) -> None:
        """load_prompt returns error for unknown subcommands."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            test_settings.prompts_path.mkdir(parents=True, exist_ok=True)

            result = load_prompt("git", "nonexistent")
            assert "Unknown command" in result

    def test_merge_strategy_append(self, test_settings: Settings) -> None:
        """load_prompt applies append merge strategy."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            test_settings.prompts_path.mkdir(parents=True, exist_ok=True)
            user_file = test_settings.prompts_path / "help.md"
            user_file.write_text("---\nmerge_strategy: append\n---\n\nUser addition")

            result = load_prompt("help")
            # Should have bundled content followed by user content
            assert "User addition" in result

    def test_merge_strategy_prepend(self, test_settings: Settings) -> None:
        """load_prompt applies prepend merge strategy."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            test_settings.prompts_path.mkdir(parents=True, exist_ok=True)
            user_file = test_settings.prompts_path / "help.md"
            user_file.write_text("---\nmerge_strategy: prepend\n---\n\nUser prefix")

            result = load_prompt("help")
            # User content should come first (note: frontmatter parsing may strip leading newline)
            assert "User prefix" in result
            assert result.index("User prefix") < result.index("$$")


class TestListAvailableCommands:
    """Tests for list_available_commands function."""

    def test_includes_bundled(self, test_settings: Settings) -> None:
        """list_available_commands includes bundled commands."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            test_settings.prompts_path.mkdir(parents=True, exist_ok=True)
            test_settings.custom_prompts_path.mkdir(parents=True, exist_ok=True)

            commands = list_available_commands()
            assert "help" in commands
            assert "git commit" in commands

    def test_includes_user_commands(self, test_settings: Settings) -> None:
        """list_available_commands includes user commands."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            test_settings.prompts_path.mkdir(parents=True, exist_ok=True)
            test_settings.custom_prompts_path.mkdir(parents=True, exist_ok=True)
            (test_settings.prompts_path / "custom.md").write_text("test")

            commands = list_available_commands()
            assert "custom" in commands

    def test_includes_custom_prompts(self, test_settings: Settings) -> None:
        """list_available_commands includes custom prompts."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            test_settings.prompts_path.mkdir(parents=True, exist_ok=True)
            test_settings.custom_prompts_path.mkdir(parents=True, exist_ok=True)
            (test_settings.custom_prompts_path / "myprompt.md").write_text("test")

            commands = list_available_commands()
            assert "myprompt" in commands

    def test_returns_sorted_unique(self, test_settings: Settings) -> None:
        """list_available_commands returns sorted unique list."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            test_settings.prompts_path.mkdir(parents=True, exist_ok=True)
            test_settings.custom_prompts_path.mkdir(parents=True, exist_ok=True)

            commands = list_available_commands()
            assert commands == sorted(set(commands))


class TestListSubcommands:
    """Tests for list_subcommands function."""

    def test_returns_bundled_subcommands(self, test_settings: Settings) -> None:
        """list_subcommands returns subcommands from bundled."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            test_settings.prompts_path.mkdir(parents=True, exist_ok=True)

            subcommands = list_subcommands("git")
            assert "commit" in subcommands

    def test_includes_user_subcommands(self, test_settings: Settings) -> None:
        """list_subcommands includes subcommands from user prompts."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            ns_dir = test_settings.prompts_path / "git"
            ns_dir.mkdir(parents=True, exist_ok=True)
            (ns_dir / "custom.md").write_text("test")

            subcommands = list_subcommands("git")
            assert "custom" in subcommands
            assert "commit" in subcommands

    def test_empty_for_unknown_namespace(self, test_settings: Settings) -> None:
        """list_subcommands returns empty for unknown namespace."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            test_settings.prompts_path.mkdir(parents=True, exist_ok=True)

            subcommands = list_subcommands("unknown")
            assert subcommands == []


class TestCustomPrompts:
    """Tests for custom prompt functions."""

    def test_save_and_load_prompt(self, test_settings: Settings) -> None:
        """save_custom_prompt and load_custom_prompt work together."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            result = save_custom_prompt("mytest", "Test prompt")
            assert "saved" in result.lower()

            loaded = load_custom_prompt("mytest")
            assert loaded == "Test prompt"

    def test_save_converts_newlines(self, test_settings: Settings) -> None:
        """save_custom_prompt converts literal \\n to newlines."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            save_custom_prompt("newline", "Line 1\\nLine 2")

            loaded = load_custom_prompt("newline")
            assert loaded == "Line 1\nLine 2"

    def test_save_empty_name_error(self, test_settings: Settings) -> None:
        """save_custom_prompt returns error for empty name."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            result = save_custom_prompt("", "content")
            assert "error" in result.lower()

    def test_load_nonexistent_returns_none(self, test_settings: Settings) -> None:
        """load_custom_prompt returns None for nonexistent prompt."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            test_settings.custom_prompts_path.mkdir(parents=True, exist_ok=True)

            result = load_custom_prompt("nonexistent")
            assert result is None

    def test_list_custom_prompts(self, test_settings: Settings) -> None:
        """list_custom_prompts returns sorted list of prompt names."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            test_settings.custom_prompts_path.mkdir(parents=True, exist_ok=True)
            (test_settings.custom_prompts_path / "zebra.md").write_text("test")
            (test_settings.custom_prompts_path / "alpha.md").write_text("test")

            prompts = list_custom_prompts()
            assert prompts == ["alpha", "zebra"]

    def test_list_custom_prompts_empty(self, test_settings: Settings) -> None:
        """list_custom_prompts returns empty list when no prompts."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            # Don't create the directory
            prompts = list_custom_prompts()
            assert prompts == []

    def test_save_and_load_nested_prompt(self, test_settings: Settings) -> None:
        """save_custom_prompt creates directories for nested prompts."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            result = save_custom_prompt("git add", "Interactive git add")
            assert "saved" in result.lower()

            loaded = load_custom_prompt("git add")
            assert loaded == "Interactive git add"

            # Verify file is in correct location
            expected_path = test_settings.custom_prompts_path / "git" / "add.md"
            assert expected_path.exists()

    def test_save_and_load_deeply_nested_prompt(self, test_settings: Settings) -> None:
        """save_custom_prompt handles multiple nesting levels."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            result = save_custom_prompt("foo bar baz qux", "Deep prompt")
            assert "saved" in result.lower()

            loaded = load_custom_prompt("foo bar baz qux")
            assert loaded == "Deep prompt"

            # Verify file is in correct location
            expected_path = (
                test_settings.custom_prompts_path / "foo" / "bar" / "baz" / "qux.md"
            )
            assert expected_path.exists()

    def test_list_custom_prompts_includes_nested(self, test_settings: Settings) -> None:
        """list_custom_prompts includes nested prompts."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            # Create flat and nested prompts
            save_custom_prompt("flat", "Flat prompt")
            save_custom_prompt("git add", "Git add")
            save_custom_prompt("foo bar baz", "Deep prompt")

            prompts = list_custom_prompts()
            assert "flat" in prompts
            assert "git add" in prompts
            assert "foo bar baz" in prompts


class TestLoadMergedPrompt:
    """Tests for load_merged_prompt function."""

    def test_loads_from_bundled(self, test_settings: Settings) -> None:
        """load_merged_prompt loads from bundled when no custom exists."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            test_settings.custom_prompts_path.mkdir(parents=True, exist_ok=True)

            result = load_merged_prompt(["git", "commit"])
            assert result is not None
            assert "commit" in result.lower() or "git" in result.lower()

    def test_loads_from_custom(self, test_settings: Settings) -> None:
        """load_merged_prompt loads from custom when exists."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            # Create custom prompt
            save_custom_prompt("mycommand", "Custom content")

            result = load_merged_prompt(["mycommand"])
            assert result == "Custom content"

    def test_loads_nested_custom(self, test_settings: Settings) -> None:
        """load_merged_prompt loads nested custom prompts."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            # Create nested custom prompt
            save_custom_prompt("git add", "Interactive add")

            result = load_merged_prompt(["git", "add"])
            assert result == "Interactive add"

    def test_custom_overrides_bundled(self, test_settings: Settings) -> None:
        """load_merged_prompt uses custom to override bundled (default strategy)."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            # Create custom override for bundled git/commit
            git_dir = test_settings.custom_prompts_path / "git"
            git_dir.mkdir(parents=True, exist_ok=True)
            (git_dir / "commit.md").write_text("Custom commit")

            result = load_merged_prompt(["git", "commit"])
            assert result == "Custom commit"

    def test_merge_strategy_append(self, test_settings: Settings) -> None:
        """load_merged_prompt applies append merge strategy."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            # Create custom with append strategy
            git_dir = test_settings.custom_prompts_path / "git"
            git_dir.mkdir(parents=True, exist_ok=True)
            (git_dir / "commit.md").write_text(
                "---\nmerge_strategy: append\n---\n\nCustom suffix"
            )

            result = load_merged_prompt(["git", "commit"])
            assert result is not None
            # Bundled content should come first, then custom
            assert "Custom suffix" in result
            bundled_content = load_bundled_prompt("git", "commit")
            assert bundled_content is not None
            assert bundled_content in result

    def test_merge_strategy_prepend(self, test_settings: Settings) -> None:
        """load_merged_prompt applies prepend merge strategy."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            # Create custom with prepend strategy
            git_dir = test_settings.custom_prompts_path / "git"
            git_dir.mkdir(parents=True, exist_ok=True)
            (git_dir / "commit.md").write_text(
                "---\nmerge_strategy: prepend\n---\n\nCustom prefix"
            )

            result = load_merged_prompt(["git", "commit"])
            assert result is not None
            # Custom content should come first
            assert result.startswith("Custom prefix")

    def test_returns_none_for_nonexistent(self, test_settings: Settings) -> None:
        """load_merged_prompt returns None for nonexistent prompts."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            test_settings.custom_prompts_path.mkdir(parents=True, exist_ok=True)

            result = load_merged_prompt(["nonexistent", "command"])
            assert result is None

    def test_deeply_nested_custom(self, test_settings: Settings) -> None:
        """load_merged_prompt handles deeply nested paths."""
        with patch("pal.prompts.loader.get_settings", return_value=test_settings):
            # Create deeply nested custom prompt
            save_custom_prompt("a b c d", "Deep content")

            result = load_merged_prompt(["a", "b", "c", "d"])
            assert result == "Deep content"
