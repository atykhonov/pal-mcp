"""Default instructions and loader."""

from pathlib import Path

from config import INSTRUCTIONS_DIR, FILES_DIR

# =============================================================================
# Custom Prompts Directory
# =============================================================================
PROMPTS_DIR = INSTRUCTIONS_DIR / "prompts"
PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
# Defaults
# =============================================================================
# Nested structure: namespace -> subcommand -> content
DEFAULT_INSTRUCTIONS = {
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

DEFAULT_FILES = {"CLAUDE.md": "When you see $$, call the run_pal_command tool."}


def ensure_defaults():
    """Create default instruction and file templates if they don't exist."""
    for name, content in DEFAULT_INSTRUCTIONS.items():
        if isinstance(content, dict):
            # Nested namespace (e.g., git/commit.md)
            namespace_dir = INSTRUCTIONS_DIR / name
            namespace_dir.mkdir(parents=True, exist_ok=True)
            for subcommand, subcontent in content.items():
                p = namespace_dir / f"{subcommand}.md"
                if not p.exists():
                    p.write_text(subcontent)
        else:
            # Flat command (e.g., help.md)
            p = INSTRUCTIONS_DIR / f"{name}.md"
            if not p.exists():
                p.write_text(content)

    for name, content in DEFAULT_FILES.items():
        p = FILES_DIR / name
        if not p.exists():
            p.write_text(content)


def load_instruction(namespace: str, subcommand: str | None = None) -> str:
    """Load instruction content for a command.

    Args:
        namespace: The command namespace (e.g., "git") or flat command (e.g., "help")
        subcommand: The subcommand (e.g., "commit") or None for flat commands
    """
    if subcommand:
        # Nested: namespace/subcommand.md
        p = INSTRUCTIONS_DIR / namespace / f"{subcommand}.md"
        if p.exists():
            return p.read_text(encoding="utf-8")
        # Check defaults
        if namespace in DEFAULT_INSTRUCTIONS:
            ns_defaults = DEFAULT_INSTRUCTIONS[namespace]
            if isinstance(ns_defaults, dict) and subcommand in ns_defaults:
                return ns_defaults[subcommand]
        return f"Unknown command: {namespace} {subcommand}"
    else:
        # Flat: namespace.md
        p = INSTRUCTIONS_DIR / f"{namespace}.md"
        if p.exists():
            return p.read_text(encoding="utf-8")
        content = DEFAULT_INSTRUCTIONS.get(namespace)
        if isinstance(content, str):
            return content
        return f"Unknown command: {namespace}"


def list_available_commands() -> list[str]:
    """List all available commands."""
    cmds = []

    # Flat commands (*.md in root)
    for p in INSTRUCTIONS_DIR.glob("*.md"):
        cmds.append(p.stem)

    # Nested commands (namespace/subcommand.md), excluding "prompts" dir
    for d in INSTRUCTIONS_DIR.iterdir():
        if d.is_dir() and d.name != "prompts":
            for p in d.glob("*.md"):
                cmds.append(f"{d.name} {p.stem}")

    # Add custom prompts as top-level commands
    for p in PROMPTS_DIR.glob("*.md"):
        cmds.append(p.stem)

    # Add defaults
    for name, content in DEFAULT_INSTRUCTIONS.items():
        if isinstance(content, dict):
            for subcommand in content.keys():
                cmds.append(f"{name} {subcommand}")
        else:
            cmds.append(name)

    return sorted(set(cmds))


def list_subcommands(namespace: str) -> list[str]:
    """List all available subcommands for a namespace.

    Args:
        namespace: The command namespace (e.g., "git")

    Returns:
        List of subcommand names
    """
    subcommands = []

    # Check filesystem
    namespace_dir = INSTRUCTIONS_DIR / namespace
    if namespace_dir.is_dir():
        for p in namespace_dir.glob("*.md"):
            subcommands.append(p.stem)

    # Check defaults
    if namespace in DEFAULT_INSTRUCTIONS:
        ns_defaults = DEFAULT_INSTRUCTIONS[namespace]
        if isinstance(ns_defaults, dict):
            subcommands.extend(ns_defaults.keys())

    return sorted(set(subcommands))


# =============================================================================
# Custom Prompts
# =============================================================================
def save_custom_prompt(name: str, content: str) -> str:
    """Save a custom prompt.

    Args:
        name: The prompt name (e.g., "tr")
        content: The prompt instruction (supports \\n for newlines)

    Returns:
        Success or error message
    """
    if not name:
        return "Error: Prompt name is required"

    # Convert literal \n to actual newlines
    content = content.replace("\\n", "\n")

    p = PROMPTS_DIR / f"{name}.md"
    p.write_text(content, encoding="utf-8")
    return f"Prompt '{name}' saved. Use it with: $${name} <input>"


def load_custom_prompt(name: str) -> str | None:
    """Load a custom prompt.

    Args:
        name: The prompt name

    Returns:
        Prompt content or None if not found
    """
    p = PROMPTS_DIR / f"{name}.md"
    if p.exists():
        return p.read_text(encoding="utf-8")
    return None


def get_prompt_path(name: str) -> Path:
    """Get the file path for a prompt.

    Args:
        name: The prompt name

    Returns:
        Path to the prompt file
    """
    return PROMPTS_DIR / f"{name}.md"


def list_custom_prompts() -> list[str]:
    """List all custom prompts."""
    return sorted(p.stem for p in PROMPTS_DIR.glob("*.md"))
