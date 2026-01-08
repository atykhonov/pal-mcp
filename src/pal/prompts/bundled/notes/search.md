---
# Specification for $$notes search

arguments:
  -n:
    alias: --limit
    description: Number of results
    type: integer
    required: false
    default: 10
  -t:
    alias: --tags
    description: Filter by tags (comma-separated)
    type: string
    required: false

# Search query is required
rest: text
rest_required: true
rest_description: The search query
---

# Search Notes

Full-text search across all notes.

## Execution

Execute via the `curl` tool:
```curl
curl -s -X POST 'http://meilisearch:7700/indexes/notes/search' \
  -H 'Content-Type: application/json' \
  -d '{"q":"<query>","limit":<n>}'
```

With tag filter:
```curl
curl -s -X POST 'http://meilisearch:7700/indexes/notes/search' \
  -H 'Content-Type: application/json' \
  -d '{"q":"<query>","limit":<n>,"filter":"tags = \"TAG1\" OR tags = \"TAG2\""}'
```

## Output Format

**Search for "{query}"** ({count} hits){filter_info}

| ID | Title | Tags | Created | Preview |
|----|-------|------|---------|---------|
| `{id[:8]}` | {title} | `tag1` `tag2` | {created_at[:10]} | {content[:100]}... |
