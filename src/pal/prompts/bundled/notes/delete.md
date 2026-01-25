---
# Specification for $$notes delete

arguments:
  -f:
    alias: --force
    description: Skip confirmation
    type: boolean
    required: false
    default: false

# Note ID is required
rest: text
rest_required: true
rest_description: The note ID to delete
---

# Delete Note

Delete a note by its ID.

## Execution

1. **Without -f**: First retrieve and show the note, then ask for confirmation
2. **With -f**: Delete immediately without confirmation

First, find the note (if partial UUID):
```curl
curl -s 'http://meilisearch:7700/indexes/notes/documents/<full_uuid>'
```

Then delete via the `pal_curl` tool:
```curl
curl -s -X DELETE 'http://meilisearch:7700/indexes/notes/documents/<full_uuid>'
```

## Output Format

On success:

Note deleted successfully.
**ID:** `{id[:8]}`
**Title:** {title}
