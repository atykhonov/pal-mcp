---
# Specification for $$notes list

arguments:
  -n:
    alias: --limit
    description: Number of notes to show
    type: integer
    required: false
    default: 20
  -t:
    alias: --tags
    description: Filter by tags (comma-separated)
    type: string
    required: false

# No rest content expected
rest: none
---

# List Notes

List recent notes from the Meilisearch index.

## Execution

Execute via the `pal_curl` tool:
```curl
curl -s -X POST 'http://meilisearch:7700/indexes/notes/search' \
  -H 'Content-Type: application/json' \
  -d '{"q": "", "limit": <n>, "sort": ["created_at:desc"]}'
```

With tag filter:
```curl
curl -s -X POST 'http://meilisearch:7700/indexes/notes/search' \
  -H 'Content-Type: application/json' \
  -d '{"q": "", "limit": <n>, "sort": ["created_at:desc"], "filter": "tags = \"TAG1\" OR tags = \"TAG2\""}'
```

## Output Format

Display as a markdown table or list:

**{count} note(s)**{filter_info}

| ID | Title | Tags | Created | Preview |
|----|-------|------|---------|---------|
| `{id[:8]}` | {title} | `tag1` `tag2` | {created_at[:10]} | {content[:100]}... |
