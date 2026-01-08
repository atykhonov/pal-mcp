---
# Specification for $$notes tags

arguments:
  -a:
    alias: --add
    description: Add tags without removing existing ones
    type: boolean
    required: false
    default: false
  -r:
    alias: --remove
    description: Remove specified tags instead of replacing
    type: boolean
    required: false
    default: false

# Note ID and tags are required
rest: text
rest_required: true
rest_description: Note ID followed by comma-separated tags (e.g., "a7f3 html,css,frontend")
---

# Update Tags

Update tags on an existing note.

## Execution

1. **Get current note** via the `curl` tool:
```curl
curl -s 'http://meilisearch:7700/indexes/notes/documents/<full_uuid>'
```

2. **Update with new tags** (include all fields):
```curl
curl -s -X PUT 'http://meilisearch:7700/indexes/notes/documents' \
  -H 'Content-Type: application/json' \
  -d '[{"id":"<id>","title":"<title>","content":"<content>","tags":["new1","new2"],"created_at":"<created_at>"}]'
```

## Tag Operations

- **Default (replace)**: Replace all tags with provided tags
- **--add**: Merge provided tags with existing tags
- **--remove**: Remove specified tags from existing tags

## Output Format

On success:

Tags updated successfully.
**Note:** {title}
**Old tags:** `old1` `old2`
**New tags:** `new1` `new2`
