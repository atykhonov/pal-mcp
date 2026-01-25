---
# Specification for $$notes view

arguments: {}

# Note ID is required
rest: text
rest_required: true
rest_description: The note ID (full UUID or 8-character prefix)
---

# View Note

Retrieve a specific note by its ID.

## Execution

For full UUID, execute via the `pal_curl` tool:
```curl
curl -s 'http://meilisearch:7700/indexes/notes/documents/<full_uuid>'
```

For partial UUID (8+ characters), search first:
```curl
curl -s -X POST 'http://meilisearch:7700/indexes/notes/search' \
  -H 'Content-Type: application/json' \
  -d '{"q": "<partial_id>", "limit": 10}'
```
Then filter results where `id` starts with the partial UUID.

## Output Format

Display the full note:

### {title}
**ID:** `{id}`
**Tags:** `tag1` `tag2`
**Created:** {created_at[:10]}

{content}
