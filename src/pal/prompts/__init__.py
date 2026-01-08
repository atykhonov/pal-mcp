"""Prompts module for loading and managing command prompts."""

from pal.prompts.defaults import DEFAULT_FILES
from pal.prompts.loader import (
    ensure_defaults,
    get_bundled_prompts_path,
    get_merge_strategy,
    get_prompt_path,
    list_available_commands,
    list_builtin_prompts,
    list_custom_prompts,
    list_subcommands,
    load_bundled_prompt,
    load_custom_prompt,
    load_prompt,
    merge_prompts,
    parse_frontmatter,
    save_custom_prompt,
)

__all__ = [
    "DEFAULT_FILES",
    "ensure_defaults",
    "get_bundled_prompts_path",
    "get_merge_strategy",
    "get_prompt_path",
    "list_available_commands",
    "list_builtin_prompts",
    "list_custom_prompts",
    "list_subcommands",
    "load_bundled_prompt",
    "load_custom_prompt",
    "load_prompt",
    "merge_prompts",
    "parse_frontmatter",
    "save_custom_prompt",
]
