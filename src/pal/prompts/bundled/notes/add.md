---
# Specification for $$notes add

arguments:
  -t:
    alias: --tags
    description: Comma-separated tags (e.g., -t work,meeting)
    type: string
    required: false

# Everything after arguments is treated as the note content
rest: text
rest_required: true
rest_description: The note content to add
---

# Add Note

Add a new note to the Meilisearch index.

## Execution

1. **Parse tags** (optional): `-t tag1,tag2` or `--tags tag1,tag2`

2. **Generate metadata**:
   - `id`: Generate a UUID v4 (e.g., `550e8400-e29b-41d4-a716-446655440000`)
   - `title`: First sentence or first 50 characters of content
   - `tags`: User-provided tags + 2-3 auto-extracted keywords from content
   - `created_at`: ISO 8601 timestamp (e.g., `2024-01-15T10:30:00Z`)

3. **Save to Meilisearch** via the `curl` tool:
```curl
curl -s -X POST 'http://meilisearch:7700/indexes/notes/documents' \
  -H 'Content-Type: application/json' \
  -d '[{"id":"<id>","title":"<title>","content":"<content>","tags":["tag1","tag2"],"created_at":"<timestamp>"}]'
```

## Output Format

On success:

Note added successfully.
**ID:** `{id[:8]}`
**Title:** {title}
**Tags:** `tag1` `tag2`

## Examples

Input: `add -t meeting,work Today we discussed Q4 priorities`
→ Tags: [meeting, work, Q4, priorities]

Input: `add Quick note about Docker networking`
→ Tags: [docker, networking] (auto-extracted)
