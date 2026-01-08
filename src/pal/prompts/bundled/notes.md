Manage notes with full-text and AI search.

**IMPORTANT:** Execute all curl commands using the `curl` MCP tool, not bash. Pass the full curl command string to the tool.

## Subcommands

Parse the input to determine which subcommand to execute:

### `add [-t tags | --tags tags] <content>`
Add a new note to Meilisearch.

1. **Parse tags** (optional):
   - `-t tag1,tag2,tag3` or `--tags tag1,tag2,tag3`
   - Tags are comma-separated, no spaces around commas

2. **Generate metadata**:
   - `id`: Generate a UUID (e.g., `550e8400-e29b-41d4-a716-446655440000` format)
   - `title`: First sentence or first 50 characters of content
   - `tags`: Combine user-provided tags with 2-3 auto-extracted keywords from content
   - `created_at`: Current ISO timestamp (e.g., `2026-01-05T12:00:00Z`)

3. **Save to Meilisearch** using the `curl` tool:
```
curl -s -X POST 'http://meilisearch:7700/indexes/notes/documents' \
  -H 'Content-Type: application/json' \
  -d '[{"id":"<uuid>","title":"<title>","content":"<full content>","tags":["tag1","tag2"],"created_at":"<timestamp>"}]'
```

4. **Output**: Confirm the note was added with its title and tags.

---

### `list`
List recent notes using the `curl` tool:

```
curl -s -X POST 'http://meilisearch:7700/indexes/notes/search' \
  -H 'Content-Type: application/json' \
  -d '{"q": "", "limit": 20, "sort": ["created_at:desc"]}'
```

Format the output as a readable list showing:
- Title
- Tags (if any)
- Created date
- First 100 characters of content

---

### `search <query>`
Regular full-text search using the `curl` tool:

```
curl -s -X POST 'http://meilisearch:7700/indexes/notes/search' \
  -H 'Content-Type: application/json' \
  -d '{"q":"<query>","limit":10}'
```

Format results showing title, tags, and a snippet of matching content.

---

### `ai <query>`
AI-powered semantic search using embeddings. Use the `curl` tool:

```
curl -s -X POST 'http://meilisearch:7700/indexes/notes/search' \
  -H 'Content-Type: application/json' \
  -d '{"q":"<query>","limit":10,"hybrid":{"semanticRatio":0.9,"embedder":"ollama"}}'
```

Format results showing title, tags, and content snippet. Note that these results are based on semantic similarity, not just keyword matching.

---

### `view <id>`
View a note by its ID (full or partial UUID). Use the `curl` tool:

For full UUID:
```
curl -s 'http://meilisearch:7700/indexes/notes/documents/<full_uuid>'
```

For partial UUID, search first then filter:
```
curl -s -X POST 'http://meilisearch:7700/indexes/notes/search' \
  -H 'Content-Type: application/json' \
  -d '{"q":"<partial_id>","limit":10}'
```
Then filter results where `id` starts with the partial UUID.

Display the full note content.

---

### `delete <id>`
Delete a note by its ID (full or partial UUID).

1. First find the note (same as `view`) to get the full UUID
2. Delete using the `curl` tool:
```
curl -s -X DELETE 'http://meilisearch:7700/indexes/notes/documents/<full_uuid>'
```

Confirm deletion with the note title.

---

### `tags <id> <tag1,tag2,...>`
Update tags on an existing note.

1. First fetch the note to get current data
2. Update with new tags using the `curl` tool:
```
curl -s -X PUT 'http://meilisearch:7700/indexes/notes/documents' \
  -H 'Content-Type: application/json' \
  -d '[{"id":"<id>","title":"<title>","content":"<content>","tags":["new1","new2"],"created_at":"<created_at>"}]'
```

Show old tags vs new tags.

---

## Error Handling

- If Meilisearch is not running or returns connection errors, inform the user that the notes service is unavailable.

## Examples

Input: `add -t meeting,work Today we discussed the Q4 roadmap and priorities`
→ Add note with tags [meeting, work] + auto-extracted tags

Input: `add This is a quick note about Docker networking`
→ Add note with auto-extracted tags only

Input: `list`
→ Show recent 20 notes

Input: `search docker`
→ Text search for "docker"

Input: `ai how do containers communicate`
→ Semantic search for container communication concepts

Input: `view a7f3b2c1`
→ View note with ID starting with a7f3b2c1

Input: `delete 6ce3`
→ Delete note with ID starting with 6ce3

Input: `tags a7f3 html,css,frontend`
→ Update tags on note a7f3...
