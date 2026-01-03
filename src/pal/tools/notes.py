"""Notes command handler with direct Meilisearch integration."""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from pal.config import get_settings
from pal.tools.parser import ParsedCommand
from pal.tools.types import CommandResult

logger = logging.getLogger(__name__)

# Timeout for Meilisearch requests
REQUEST_TIMEOUT = 10.0


def handle_notes(command: ParsedCommand) -> CommandResult | None:
    """Handle notes commands with direct Meilisearch integration.

    Subcommands:
        add [-t tags] <content> - Add a new note
        list [-t tags] - List recent notes (optionally filtered by tags)
        view <id> - View full note by ID (partial UUID supported)
        load <id> - Load note quietly
        tags <id> <tags> - Update tags on a note
        delete <id> - Delete a note by ID
        search [-t tags] <query> - Full-text search (optionally filtered by tags)
        ai [-t tags] <query> - AI semantic search (optionally filtered by tags)
        help - Show available commands

    Tag filtering:
        Use -t tag1,tag2 or --tags tag1,tag2 to filter by tags.
    """
    if command.namespace != "notes":
        return None

    settings = get_settings()
    if not settings.meilisearch_url:
        # Fall back to prompt-based approach if Meilisearch URL not configured
        return None

    subcommand = command.subcommand or ""
    rest = command.rest or ""

    # Combine subcommand and rest for parsing
    full_input = f"{subcommand} {rest}".strip() if subcommand else rest

    if full_input.startswith("add ") or full_input == "add":
        return _handle_add(
            settings.meilisearch_url,
            settings.ollama_url,
            settings.ollama_model,
            settings.notes_ai_provider,
            full_input[4:].strip(),
        )
    elif full_input == "list" or full_input.startswith("list "):
        # Parse tag filters: $$notes list -t tag1,tag2
        list_args = full_input[4:].strip() if full_input.startswith("list ") else ""
        filter_tags, _ = _parse_tag_filter(list_args)
        return _handle_list(settings.meilisearch_url, filter_tags)
    elif full_input.startswith("search "):
        # Parse tag filters: $$notes search -t tag1,tag2 "query"
        search_args = full_input[7:].strip()
        filter_tags, query = _parse_tag_filter(search_args)
        return _handle_search(settings.meilisearch_url, query, filter_tags)
    elif full_input.startswith("ai "):
        # Parse tag filters: $$notes ai -t tag1,tag2 "query"
        ai_args = full_input[3:].strip()
        filter_tags, query = _parse_tag_filter(ai_args)
        return _handle_ai_search(settings.meilisearch_url, query, filter_tags)
    elif full_input.startswith("view "):
        return _handle_view(settings.meilisearch_url, full_input[5:].strip())
    elif full_input.startswith("load "):
        # load is an alias for view with quiet=True
        return _handle_view(settings.meilisearch_url, full_input[5:].strip(), quiet=True)
    elif full_input.startswith("tags "):
        return _handle_tags(settings.meilisearch_url, full_input[5:].strip())
    elif full_input.startswith("delete "):
        return _handle_delete(settings.meilisearch_url, full_input[7:].strip())
    elif full_input == "help":
        return CommandResult(
            output=(
                "## $$notes help\n\n"
                "**Available commands:**\n\n"
                "- `$$notes add [-t tags] <content>` - Add a new note\n"
                "- `$$notes list [-t tags]` - List recent notes (optionally filtered by tags)\n"
                "- `$$notes view <id>` - View full note by ID (partial UUID supported)\n"
                "- `$$notes load <id>` - Load note quietly (minimal display)\n"
                "- `$$notes tags <id> <tags>` - Update tags on a note\n"
                "- `$$notes delete <id>` - Delete a note by ID\n"
                "- `$$notes search [-t tags] <query>` - Full-text search (optionally filtered by tags)\n"
                "- `$$notes ai [-t tags] <query>` - AI semantic search (optionally filtered by tags)\n\n"
                "**Tag filtering:**\n\n"
                "Use `-t tag1,tag2` or `--tags tag1,tag2` to filter by tags.\n"
                "Example: `$$notes list -t docker,kubernetes`"
            )
        )
    else:
        return CommandResult(
            output=(
                "## $$notes\n\n"
                "Unknown subcommand. Available commands:\n\n"
                "- `$$notes add [-t tags] <content>` - Add a new note\n"
                "- `$$notes list [-t tags]` - List recent notes\n"
                "- `$$notes view <id>` - View full note by ID (partial UUID supported)\n"
                "- `$$notes load <id>` - Load note quietly (minimal display)\n"
                "- `$$notes tags <id> <tags>` - Update tags on a note\n"
                "- `$$notes delete <id>` - Delete a note by ID\n"
                "- `$$notes search [-t tags] <query>` - Full-text search\n"
                "- `$$notes ai [-t tags] <query>` - AI semantic search\n\n"
                "Use `-t tag1,tag2` or `--tags tag1,tag2` to filter by tags."
            )
        )


def _parse_tag_filter(input_text: str) -> tuple[list[str], str]:
    """Parse -t/--tags flag from input.

    Args:
        input_text: Raw input string that may contain tag filters.

    Returns:
        Tuple of (tags list, remaining input without tag flags).

    Supports both forms:
        -t tag1,tag2 (with space)
        -ttag1,tag2 (without space)
        --tags tag1,tag2 (requires space)
    """
    tags: list[str] = []
    remaining = input_text

    # Match -t tags (optional space) or --tags tags (required space)
    # -t can be followed by optional whitespace: -tsql or -t sql
    # --tags requires whitespace: --tags sql
    tag_match = re.match(r"^(?:-t\s*([^\s]+)|--tags\s+([^\s]+))\s*(.*)$", input_text, re.DOTALL)
    if tag_match:
        # Group 1 is for -t, Group 2 is for --tags
        tag_value = tag_match.group(1) or tag_match.group(2)
        tags = [t.strip().lower() for t in tag_value.split(",") if t.strip()]
        remaining = tag_match.group(3).strip()

    return tags, remaining


def _build_tag_filter(tags: list[str]) -> str | None:
    """Build Meilisearch filter string for tags.

    Args:
        tags: List of tags to filter by.

    Returns:
        Meilisearch filter string or None if no tags.
    """
    if not tags:
        return None

    # Use OR to match any of the provided tags
    conditions = [f'tags = "{tag}"' for tag in tags]
    return " OR ".join(conditions)


def _generate_ai_tags(ollama_url: str, ollama_model: str, content: str) -> list[str]:
    """Generate semantic tags using Ollama AI."""
    prompt = (
        "Extract 3-5 topic tags for this note. "
        "Return ONLY comma-separated lowercase single-word tags, nothing else. "
        "Focus on the main technical concepts and topics.\n\n"
        f"{content[:1000]}"  # Limit content length for efficiency
    )

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": ollama_model,
                    "prompt": prompt,
                    "stream": False,
                },
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()

        # Parse the response
        raw_tags = data.get("response", "").strip()
        # Clean up: split by comma, strip whitespace, lowercase, remove empty
        tags = [
            t.strip().lower().replace(" ", "-")
            for t in raw_tags.split(",")
            if t.strip() and len(t.strip()) < 30
        ]
        # Filter out non-alphanumeric tags and limit to 5
        tags = [t for t in tags if re.match(r"^[a-z0-9-]+$", t)][:5]
        return tags
    except Exception as e:
        logger.warning(f"AI tag generation failed: {e}")
        return []


def _extract_keyword_tags(content: str) -> list[str]:
    """Extract keyword tags as fallback (simple approach)."""
    words = re.findall(r"\b[a-zA-Z]{4,}\b", content.lower())
    common_words = {
        "this", "that", "with", "from", "have", "been", "were", "they",
        "their", "about", "would", "could", "should", "which", "there",
        "where", "when", "what", "some", "into", "more", "other", "very",
        "just", "also", "than", "then", "only", "here", "technical", "note",
    }
    return list(dict.fromkeys(w for w in words if w not in common_words))[:3]


def _handle_add(
    meili_url: str,
    ollama_url: str,
    ollama_model: str,
    ai_provider: str,
    input_text: str,
) -> CommandResult:
    """Add a new note to Meilisearch.

    Args:
        meili_url: Meilisearch URL.
        ollama_url: Ollama URL for AI features.
        ollama_model: Ollama model name.
        ai_provider: AI provider for tag generation ('ollama', 'claude', or 'none').
        input_text: The note content with optional flags.
    """
    if not input_text:
        return CommandResult(output="## $$notes add\n\nError: No content provided.")

    # Parse tags
    user_tags: list[str] = []
    content = input_text

    # Check for -t or --tags flag
    tag_match = re.match(r"^(?:-t|--tags)\s+([^\s]+)\s+(.+)$", input_text, re.DOTALL)
    if tag_match:
        user_tags = [t.strip() for t in tag_match.group(1).split(",") if t.strip()]
        content = tag_match.group(2).strip()

    # Generate title (first sentence or first 50 chars)
    title = content.split(".")[0][:50]
    if len(title) < len(content.split(".")[0]):
        title += "..."

    # Generate AI tags based on provider
    ai_tags: list[str] = []
    claude_prompt: str | None = None

    if ai_provider == "ollama":
        # Use Ollama for tag generation (synchronous, may be slow)
        ai_tags = _generate_ai_tags(ollama_url, ollama_model, content)
        if not ai_tags:
            ai_tags = _extract_keyword_tags(content)
    elif ai_provider == "claude":
        # Use keyword extraction now, prompt Claude to suggest better tags
        ai_tags = _extract_keyword_tags(content)
        claude_prompt = content[:500]  # Content for Claude to analyze
    else:  # "none"
        # Keyword extraction only
        ai_tags = _extract_keyword_tags(content)

    # Merge user tags (priority) with AI tags
    all_tags = list(dict.fromkeys(user_tags + ai_tags))

    # Create document
    note_id = str(uuid.uuid4())
    doc = {
        "id": note_id,
        "title": title,
        "content": content,
        "tags": all_tags,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.post(
                f"{meili_url}/indexes/notes/documents",
                json=[doc],
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

        tags_str = ", ".join(f"`{t}`" for t in all_tags) if all_tags else "none"

        # Build output
        output_lines = [
            "## $$notes add\n",
            "Note added successfully.\n",
            f"**ID:** `{note_id[:8]}`",
            f"**Title:** {title}",
            f"**Tags:** {tags_str}",
        ]

        # If using Claude provider, instruct Claude to auto-apply tags
        if claude_prompt:
            output_lines.extend([
                "\n---",
                f"**Action required:** Execute `$$notes tags {note_id[:8]} <tags>` now, choosing 3-5 semantic tags from this content:\n",
                f"> {claude_prompt}",
            ])

        return CommandResult(output="\n".join(output_lines))
    except httpx.ConnectError:
        return CommandResult(
            output=(
                "## $$notes add\n\n"
                "Error: Could not connect to Meilisearch.\n\n"
                "Make sure Meilisearch is running:\n"
                "```\ncd /home/andrii/projects/notes-search && docker compose up -d\n```"
            )
        )
    except httpx.HTTPStatusError as e:
        return CommandResult(output=f"## $$notes add\n\nError: {e}")


def _handle_list(meili_url: str, filter_tags: list[str] | None = None) -> CommandResult:
    """List last 10 notes ordered by created date descending.

    Args:
        meili_url: Meilisearch URL.
        filter_tags: Optional list of tags to filter by.
    """
    try:
        search_params: dict[str, Any] = {
            "q": "",
            "limit": 10,
            "sort": ["created_at:desc"],
        }

        # Add tag filter if provided
        tag_filter = _build_tag_filter(filter_tags or [])
        if tag_filter:
            search_params["filter"] = tag_filter

        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.post(
                f"{meili_url}/indexes/notes/search",
                json=search_params,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()

        results = data.get("hits", [])
        if not results:
            if filter_tags:
                tags_str = ", ".join(f"`{t}`" for t in filter_tags)
                return CommandResult(output=f"## $$notes list\n\nNo notes found with tags: {tags_str}")
            return CommandResult(output="## $$notes list\n\nNo notes found.")

        # Build header with filter info
        header = f"## $$notes list\n\n**{len(results)} note(s)**"
        if filter_tags:
            tags_str = ", ".join(f"`{t}`" for t in filter_tags)
            header += f" (filtered by: {tags_str})"
        header += "\n"
        lines = [header]
        for note in results:
            title = note.get("title", "Untitled")
            tags = note.get("tags", [])
            created = note.get("created_at", "")[:10]
            content = note.get("content", "")[:100]
            note_id = note.get("id", "")[:8]  # Short UUID
            if len(note.get("content", "")) > 100:
                content += "..."

            tags_str = " ".join(f"`{t}`" for t in tags) if tags else ""
            lines.append(f"### {title}")
            lines.append(f"**ID:** `{note_id}` **Created:** {created}")
            if tags_str:
                lines.append(f"**Tags:** {tags_str}")
            lines.append(f"\n{content}\n")

        return CommandResult(output="\n".join(lines))
    except httpx.ConnectError:
        return CommandResult(
            output=(
                "## $$notes list\n\n"
                "Error: Could not connect to Meilisearch.\n\n"
                "Make sure Meilisearch is running:\n"
                "```\ncd /home/andrii/projects/notes-search && docker compose up -d\n```"
            )
        )
    except httpx.HTTPStatusError as e:
        return CommandResult(output=f"## $$notes list\n\nError: {e}")


def _handle_search(
    meili_url: str, query: str, filter_tags: list[str] | None = None
) -> CommandResult:
    """Full-text search in notes.

    Args:
        meili_url: Meilisearch URL.
        query: Search query.
        filter_tags: Optional list of tags to filter by.
    """
    query = query.strip('"\'')
    if not query:
        return CommandResult(output="## $$notes search\n\nError: No query provided.")

    try:
        search_params: dict[str, Any] = {"q": query, "limit": 10}

        # Add tag filter if provided
        tag_filter = _build_tag_filter(filter_tags or [])
        if tag_filter:
            search_params["filter"] = tag_filter

        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.post(
                f"{meili_url}/indexes/notes/search",
                json=search_params,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()

        return _format_search_results(query, data, "search", filter_tags)
    except httpx.ConnectError:
        return CommandResult(
            output=(
                "## $$notes search\n\n"
                "Error: Could not connect to Meilisearch.\n\n"
                "Make sure Meilisearch is running:\n"
                "```\ncd /home/andrii/projects/notes-search && docker compose up -d\n```"
            )
        )
    except httpx.HTTPStatusError as e:
        return CommandResult(output=f"## $$notes search\n\nError: {e}")


def _handle_ai_search(
    meili_url: str, query: str, filter_tags: list[str] | None = None
) -> CommandResult:
    """AI-powered semantic search in notes.

    Args:
        meili_url: Meilisearch URL.
        query: Search query.
        filter_tags: Optional list of tags to filter by.
    """
    query = query.strip('"\'')
    if not query:
        return CommandResult(output="## $$notes ai\n\nError: No query provided.")

    try:
        search_params: dict[str, Any] = {
            "q": query,
            "limit": 10,
            "hybrid": {"semanticRatio": 0.9, "embedder": "ollama"},
        }

        # Add tag filter if provided
        tag_filter = _build_tag_filter(filter_tags or [])
        if tag_filter:
            search_params["filter"] = tag_filter

        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.post(
                f"{meili_url}/indexes/notes/search",
                json=search_params,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()

        return _format_search_results(query, data, "ai", filter_tags)
    except httpx.ConnectError:
        return CommandResult(
            output=(
                "## $$notes ai\n\n"
                "Error: Could not connect to Meilisearch.\n\n"
                "Make sure Meilisearch is running:\n"
                "```\ncd /home/andrii/projects/notes-search && docker compose up -d\n```"
            )
        )
    except httpx.HTTPStatusError as e:
        return CommandResult(output=f"## $$notes ai\n\nError: {e}")


def _get_note_by_index(meili_url: str, index: int) -> dict[str, Any] | None:
    """Get a note by its 1-based index from the list."""
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.get(f"{meili_url}/indexes/notes/documents?limit=100")
            response.raise_for_status()
            data = response.json()

        results = data.get("results", [])
        if 1 <= index <= len(results):
            return results[index - 1]
        return None
    except (httpx.ConnectError, httpx.HTTPStatusError):
        return None


def _get_note_by_id(meili_url: str, note_id: str) -> dict[str, Any] | None:
    """Get a note by its UUID or partial UUID prefix.

    Supports both full UUIDs and partial prefixes (e.g., 'f4b53ac2').
    """
    note_id = note_id.lower()

    # First try exact match (full UUID)
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.get(f"{meili_url}/indexes/notes/documents/{note_id}")
            if response.status_code == 200:
                return response.json()
    except httpx.ConnectError:
        return None

    # If not found, try partial UUID match
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.get(f"{meili_url}/indexes/notes/documents?limit=100")
            response.raise_for_status()
            data = response.json()

        results = data.get("results", [])
        matches = [n for n in results if n.get("id", "").lower().startswith(note_id)]

        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            # Multiple matches - return None and let caller handle ambiguity
            return None
        return None
    except (httpx.ConnectError, httpx.HTTPStatusError):
        return None


def _handle_view(meili_url: str, input_text: str, quiet: bool = False) -> CommandResult:
    """Show a full note by ID (partial UUID supported) or index.

    Args:
        meili_url: Meilisearch URL.
        input_text: Note ID (full or partial UUID) or index.
        quiet: If True, return minimal display with full content in context.
    """
    if not input_text:
        return CommandResult(output="## $$notes view\n\nError: No note ID provided.")

    # Parse -q/--quiet flag
    parts = input_text.split()
    note_id = None
    for part in parts:
        if part in ("-q", "--quiet"):
            quiet = True
        else:
            note_id = part

    if not note_id:
        return CommandResult(output="## $$notes view\n\nError: No note ID provided.")

    # Try as numeric index first
    note = None
    if note_id.isdigit():
        note = _get_note_by_index(meili_url, int(note_id))
    else:
        note = _get_note_by_id(meili_url, note_id)

    if not note:
        return CommandResult(
            output=f"## $$notes view\n\nError: Note '{note_id}' not found."
        )

    title = note.get("title", "Untitled")
    tags = note.get("tags", [])
    created = note.get("created_at", "")[:10]
    content = note.get("content", "")
    note_uuid = note.get("id", "")

    tags_str = " ".join(f"`{t}`" for t in tags) if tags else "none"

    full_output = (
        f"### {title}\n"
        f"**ID:** `{note_uuid}`\n"
        f"**Tags:** {tags_str}\n"
        f"**Created:** {created}\n\n"
        f"{content}"
    )

    if quiet:
        return CommandResult(
            output=full_output,
            display=f"## $$notes load\n\nNote **{title}** loaded into context.",
        )

    return CommandResult(output=f"## $$notes view\n\n{full_output}")


def _handle_tags(meili_url: str, input_text: str) -> CommandResult:
    """Update tags on an existing note."""
    if not input_text:
        return CommandResult(
            output="## $$notes tags\n\nUsage: `$$notes tags <id> <tag1,tag2,...>`"
        )

    # Parse: first arg is note ID, rest is tags
    parts = input_text.split(None, 1)
    if len(parts) < 2:
        return CommandResult(
            output="## $$notes tags\n\nUsage: `$$notes tags <id> <tag1,tag2,...>`"
        )

    note_id, tags_str = parts
    new_tags = [t.strip() for t in tags_str.split(",") if t.strip()]

    if not new_tags:
        return CommandResult(
            output="## $$notes tags\n\nError: No tags provided."
        )

    # Get the note
    note = None
    if note_id.isdigit():
        note = _get_note_by_index(meili_url, int(note_id))
    else:
        note = _get_note_by_id(meili_url, note_id)

    if not note:
        return CommandResult(
            output=f"## $$notes tags\n\nError: Note '{note_id}' not found."
        )

    old_tags = note.get("tags", [])
    note["tags"] = new_tags

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.put(
                f"{meili_url}/indexes/notes/documents",
                json=[note],
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

        old_tags_str = ", ".join(f"`{t}`" for t in old_tags) if old_tags else "none"
        new_tags_str = ", ".join(f"`{t}`" for t in new_tags)

        return CommandResult(
            output=(
                f"## $$notes tags\n\n"
                f"Tags updated successfully.\n\n"
                f"**Note:** {note.get('title', 'Untitled')}\n"
                f"**Old tags:** {old_tags_str}\n"
                f"**New tags:** {new_tags_str}"
            )
        )
    except httpx.ConnectError:
        return CommandResult(
            output=(
                "## $$notes tags\n\n"
                "Error: Could not connect to Meilisearch.\n\n"
                "Make sure Meilisearch is running:\n"
                "```\ncd /home/andrii/projects/notes-search && docker compose up -d\n```"
            )
        )
    except httpx.HTTPStatusError as e:
        return CommandResult(output=f"## $$notes tags\n\nError: {e}")


def _handle_delete(meili_url: str, note_id: str) -> CommandResult:
    """Delete a note by ID.

    Args:
        meili_url: Meilisearch URL.
        note_id: Note ID (full or partial UUID).
    """
    if not note_id:
        return CommandResult(output="## $$notes delete\n\nError: No note ID provided.")

    # Get the note first to show what was deleted
    note = None
    if note_id.isdigit():
        note = _get_note_by_index(meili_url, int(note_id))
    else:
        note = _get_note_by_id(meili_url, note_id)

    if not note:
        return CommandResult(
            output=f"## $$notes delete\n\nError: Note '{note_id}' not found."
        )

    full_id = note.get("id", "")
    title = note.get("title", "Untitled")

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.delete(
                f"{meili_url}/indexes/notes/documents/{full_id}",
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

        return CommandResult(
            output=(
                f"## $$notes delete\n\n"
                f"Note deleted successfully.\n\n"
                f"**ID:** `{full_id[:8]}`\n"
                f"**Title:** {title}"
            )
        )
    except httpx.ConnectError:
        return CommandResult(
            output=(
                "## $$notes delete\n\n"
                "Error: Could not connect to Meilisearch.\n\n"
                "Make sure Meilisearch is running:\n"
                "```\ncd /home/andrii/projects/notes-search && docker compose up -d\n```"
            )
        )
    except httpx.HTTPStatusError as e:
        return CommandResult(output=f"## $$notes delete\n\nError: {e}")


def _format_search_results(
    query: str,
    data: dict[str, Any],
    search_type: str,
    filter_tags: list[str] | None = None,
) -> CommandResult:
    """Format search results for display."""
    hits = data.get("hits", [])
    semantic_count = data.get("semanticHitCount", 0)

    header = f"## $$notes {search_type}\n\n"
    if search_type == "ai":
        header += f'**AI Search for "{query}"** ({len(hits)} hits, {semantic_count} semantic)'
    else:
        header += f'**Search for "{query}"** ({len(hits)} hits)'

    if filter_tags:
        tags_str = ", ".join(f"`{t}`" for t in filter_tags)
        header += f" (filtered by: {tags_str})"
    header += "\n"

    if not hits:
        return CommandResult(output=header + "\nNo results found.")

    lines = [header]
    for hit in hits:
        title = hit.get("title", "Untitled")
        tags = hit.get("tags", [])
        created = hit.get("created_at", "")[:10]
        content = hit.get("content", "")[:100]
        note_id = hit.get("id", "")[:8]  # Short UUID
        if len(hit.get("content", "")) > 100:
            content += "..."

        tags_str = " ".join(f"`{t}`" for t in tags) if tags else ""
        lines.append(f"### {title}")
        lines.append(f"**ID:** `{note_id}` **Created:** {created}")
        if tags_str:
            lines.append(f"**Tags:** {tags_str}")
        lines.append(f"\n{content}\n")

    return CommandResult(output="\n".join(lines))
