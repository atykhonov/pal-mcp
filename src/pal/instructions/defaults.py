"""Default instructions and file templates."""

from __future__ import annotations

from typing import TypeAlias

# Type aliases for instruction structures
InstructionContent: TypeAlias = str | dict[str, str]
InstructionDict: TypeAlias = dict[str, InstructionContent]

DEFAULT_INSTRUCTIONS: InstructionDict = {
    "curl": """Execute HTTP requests via the `curl` MCP tool.

## MCP Tool
Call `curl` with parameters:
- `command` (required): Full curl command string
- `timeout` (optional): Timeout in seconds (default 30)

## Usage
The curl tool executes curl commands on the server. Use it when instructions specify:

```
Execute via the `curl` tool:
```curl
curl -s 'http://meilisearch:7700/health'
```
```

For native execution, instructions will specify:

```
Execute directly via Bash:
```bash
curl -s 'http://meilisearch:7700/health'
```
```

## Response Format
```json
{
  "success": true,
  "output": "response body"
}
```

On error:
```json
{
  "success": false,
  "output": "",
  "error": "error message"
}
```

## Supported Flags
All standard curl flags are supported: -s, -X, -H, -d, --data-raw, etc.
""",
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
    "notes": {
        "list": """List recent notes from the database.

## Curl Command
Execute via the `curl` tool:
```curl
curl -s -X POST 'http://meilisearch:7700/indexes/notes/search' \
  -H 'Content-Type: application/json' \
  -d '{"q": "", "limit": 20, "sort": ["created_at:desc"]}'
```

With tag filter (replace TAG1,TAG2 with actual tags):
```curl
curl -s -X POST 'http://meilisearch:7700/indexes/notes/search' \
  -H 'Content-Type: application/json' \
  -d '{"q": "", "limit": 10, "sort": ["created_at:desc"], "filter": "tags = \\"TAG1\\" OR tags = \\"TAG2\\""}'
```

## Output Format
Display results as:

**{count} note(s)**{filter_info}

For each note in `hits` array:
### {title}
**ID:** `{id[:8]}` **Created:** {created_at[:10]}
**Tags:** `tag1` `tag2`

{content[:100]}...
""",
        "add": """Add a new note to the database.

## Step 1: Generate Tags
First, analyze the content and generate 3-5 semantic tags (lowercase, single words or hyphenated).

## Step 2: Create Note
Execute via the `curl` tool (replace GENERATED_UUID, TITLE, CONTENT, TAGS, TIMESTAMP):
```curl
curl -s -X POST 'http://meilisearch:7700/indexes/notes/documents' \
  -H 'Content-Type: application/json' \
  -d '[{"id": "GENERATED_UUID", "title": "TITLE", "content": "CONTENT", "tags": ["tag1", "tag2"], "created_at": "TIMESTAMP"}]'
```

Notes:
- Generate a UUID v4 for the id field
- Title: first sentence or first 50 chars of content
- Timestamp: ISO 8601 format (e.g., 2024-01-15T10:30:00Z)
- Escape special characters in JSON

## Output Format
On success:

Note added successfully.
**ID:** `{id[:8]}`
**Title:** {title}
**Tags:** `tag1` `tag2`
""",
        "view": """View a note by ID.

## Curl Command
For full UUID, execute via the `curl` tool:
```curl
curl -s 'http://meilisearch:7700/indexes/notes/documents/{full_uuid}'
```

For partial UUID, search first:
```curl
curl -s -X POST 'http://meilisearch:7700/indexes/notes/search' \
  -H 'Content-Type: application/json' \
  -d '{"q": "{partial_id}", "limit": 10}'
```
Then filter results where `id` starts with the partial UUID.

## Output Format
### {title}
**ID:** `{id}`
**Tags:** `tag1` `tag2`
**Created:** {created_at[:10]}

{content}
""",
        "delete": """Delete a note by ID.

## Step 1: Find the Note
If partial UUID, first search to get full ID (see `$$notes view`).

## Step 2: Delete
Execute via the `curl` tool:
```curl
curl -s -X DELETE 'http://meilisearch:7700/indexes/notes/documents/{full_uuid}'
```

## Output Format
On success:

Note deleted successfully.
**ID:** `{id[:8]}`
**Title:** {title}
""",
        "tags": """Update tags on an existing note.

## Step 1: Get Current Note
Execute via the `curl` tool:
```curl
curl -s 'http://meilisearch:7700/indexes/notes/documents/{full_uuid}'
```

## Step 2: Update with New Tags
Execute via the `curl` tool (include all fields, update only tags):
```curl
curl -s -X PUT 'http://meilisearch:7700/indexes/notes/documents' \
  -H 'Content-Type: application/json' \
  -d '[{"id": "{id}", "title": "{title}", "content": "{content}", "tags": ["new1", "new2"], "created_at": "{created_at}"}]'
```

## Output Format
On success:

Tags updated successfully.
**Note:** {title}
**Old tags:** `old1` `old2`
**New tags:** `new1` `new2`
""",
        "search": """Full-text search in notes.

## Curl Command
Execute via the `curl` tool:
```curl
curl -s -X POST 'http://meilisearch:7700/indexes/notes/search' \
  -H 'Content-Type: application/json' \
  -d '{"q": "SEARCH_QUERY", "limit": 10}'
```

With tag filter:
```curl
curl -s -X POST 'http://meilisearch:7700/indexes/notes/search' \
  -H 'Content-Type: application/json' \
  -d '{"q": "SEARCH_QUERY", "limit": 10, "filter": "tags = \\"TAG1\\" OR tags = \\"TAG2\\""}'
```

## Output Format
**Search for "{query}"** ({count} hits){filter_info}

For each hit in `hits` array (same format as list).
""",
        "ai": """AI-powered semantic search using embeddings.

## Curl Command
Execute via the `curl` tool:
```curl
curl -s -X POST 'http://meilisearch:7700/indexes/notes/search' \
  -H 'Content-Type: application/json' \
  -d '{"q": "SEARCH_QUERY", "limit": 10, "hybrid": {"semanticRatio": 0.9, "embedder": "ollama"}}'
```

With tag filter:
```curl
curl -s -X POST 'http://meilisearch:7700/indexes/notes/search' \
  -H 'Content-Type: application/json' \
  -d '{"q": "SEARCH_QUERY", "limit": 10, "hybrid": {"semanticRatio": 0.9, "embedder": "ollama"}, "filter": "tags = \\"TAG1\\""}'
```

## Output Format
**AI Search for "{query}"** ({count} hits, {semanticHitCount} semantic){filter_info}

For each hit in `hits` array (same format as list).
""",
        "help": """Show available notes commands.

## Available Commands
- `$$notes list [-t tags]` - List recent notes
- `$$notes add [-t tags] <content>` - Add a new note
- `$$notes view <id>` - View full note by ID
- `$$notes delete <id>` - Delete a note by ID
- `$$notes tags <id> <tags>` - Update tags on a note
- `$$notes search [-t tags] <query>` - Full-text search
- `$$notes ai [-t tags] <query>` - AI semantic search

## Tag Filtering
Use `-t tag1,tag2` to filter by tags.

## API Base URL
All commands use Meilisearch at `http://meilisearch:7700`.
""",
    },
    "help": "Use $$git commit",
}

DEFAULT_FILES: dict[str, str] = {
    "CLAUDE.md": "When you see $$, call the run_pal_command tool.",
}
