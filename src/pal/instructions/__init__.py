"""Instructions module for loading and managing command instructions."""

from pal.instructions.defaults import DEFAULT_FILES, DEFAULT_INSTRUCTIONS
from pal.instructions.loader import (
    ensure_defaults,
    get_prompt_path,
    list_available_commands,
    list_custom_prompts,
    list_subcommands,
    load_custom_prompt,
    load_instruction,
    save_custom_prompt,
)

__all__ = [
    "DEFAULT_FILES",
    "DEFAULT_INSTRUCTIONS",
    "ensure_defaults",
    "get_prompt_path",
    "list_available_commands",
    "list_custom_prompts",
    "list_subcommands",
    "load_custom_prompt",
    "load_instruction",
    "save_custom_prompt",
]
