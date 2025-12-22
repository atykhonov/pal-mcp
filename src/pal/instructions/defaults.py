"""Default instructions and file templates."""

from __future__ import annotations

from typing import TypeAlias

# Type aliases for instruction structures
InstructionContent: TypeAlias = str | dict[str, str]
InstructionDict: TypeAlias = dict[str, InstructionContent]

DEFAULT_INSTRUCTIONS: InstructionDict = {
    "git": {
        "commit": """Create a git commit with the following rules:

1. Use conventional commit format: type(scope): description
2. Types: feat, fix, docs, style, refactor, test, chore
3. First line maximum 72 characters
4. Use imperative mood ("add" not "added")
5. No period at the end of subject line

CRITICAL - DO NOT ADD:
- "Generated with [Claude Code](https://claude.com/claude-code)"
- "Co-Authored-By: Claude <noreply@anthropic.com>"
- Any AI attribution or signatures
- Any Co-authored-by lines
- Emoji (unless user explicitly asks)

If the user provided a description, use it to create the commit message.
If no description, analyze staged changes with `git diff --cached` and create an appropriate message.

After creating the message, run `git commit -m "your message"`.
""",
    },
    "help": "Use $$git commit",
}

DEFAULT_FILES: dict[str, str] = {
    "CLAUDE.md": "When you see $$, call the run_pal_command tool.",
}
