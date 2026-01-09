Retrieve and manage tagged content for current conversation session.

**IMPORTANT:** Execute all curl commands using the `curl` MCP tool, not bash. Pass the full curl command string to the tool.

## Session UUID

**CRITICAL:** Use the SAME SESSION_UUID that was used when tagging content in this conversation. If you haven't used `$$tag` yet in this conversation, you won't have any tagged items to retrieve.

If you don't remember the SESSION_UUID from earlier in this conversation, inform the user that no session is active and they should tag something first with `$$tag`.

## Subcommands

Parse the input to determine which subcommand to execute. All queries MUST filter by your SESSION_UUID.

### `<tag>` (default - get by tag)
Retrieve all content with a specific tag.

```
curl -s -X POST 'http://meilisearch:7700/indexes/tags/search' \
  -H 'Content-Type: application/json' \
  -d '{"q":"","filter":"session_id = \"<SESSION_UUID>\" AND tags = \"<tag>\"","limit":20,"sort":["created_at:desc"]}'
```

Output the content of matching items, separated by `---`.

---

### `list`
List recent tagged items for current session.

```
curl -s -X POST 'http://meilisearch:7700/indexes/tags/search' \
  -H 'Content-Type: application/json' \
  -d '{"q":"","filter":"session_id = \"<SESSION_UUID>\"","limit":20,"sort":["created_at:desc"]}'
```

Format output showing:
- Session UUID (for reference)
- For each item: Tags, first 100 characters of content, created date

---

### `search <query>`
Full-text search within tagged items for current session.

```
curl -s -X POST 'http://meilisearch:7700/indexes/tags/search' \
  -H 'Content-Type: application/json' \
  -d '{"q":"<query>","filter":"session_id = \"<SESSION_UUID>\"","limit":10}'
```

Format results showing tags and matching content snippet.

---

### `view <id>`
View full content of a tagged item by ID (full or partial UUID).

```
curl -s 'http://meilisearch:7700/indexes/tags/documents/<full_uuid>'
```

For partial UUID, search first then filter by ID prefix.

---

### `delete <id>`
Delete a tagged item by ID.

1. Find the item (same as `view`) to get full UUID
2. Delete:
```
curl -s -X DELETE 'http://meilisearch:7700/indexes/tags/documents/<full_uuid>'
```

Confirm deletion.

---

## Example Output for `list`

```
Session: a1b2c3d4-e5f6-7890-abcd-ef1234567890

1. [code, python] "def hello_world():..." (2 min ago)
2. [notes, meeting] "Discussed the new API..." (5 min ago)
```

## Error Handling

- If no SESSION_UUID is known, inform user to tag something first with `$$tag`
- If no items found, inform the user
- If Meilisearch is unavailable, report the error
- All queries are scoped to SESSION_UUID - items from other sessions/conversations are not visible
