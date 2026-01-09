Tag and retrieve content by labels, scoped to conversation session.

**IMPORTANT:** Execute all curl commands using the `curl` MCP tool, not bash. Pass the full curl command string to the tool.

## Session UUID

**CRITICAL:** Before your first tag operation in this conversation, generate a random UUID (e.g., `a1b2c3d4-e5f6-7890-abcd-ef1234567890`) and remember it as your SESSION_UUID. Use this SAME UUID for ALL tag operations throughout this conversation.

If you've already generated a SESSION_UUID earlier in this conversation, use that same one.

## Usage

```
$$tag tag1,tag2[,tag3...] [content]
```

If no content provided, defaults to `$REPLY` (your last response).

## Execution

1. **Get or generate SESSION_UUID**: Use existing UUID from this conversation, or generate a new one if this is the first tag operation
2. **Parse tags**: Extract comma-separated tags from first argument
3. **Get content**: Use provided content, or `$REPLY` if none
4. **Generate metadata**:
   - `id`: Generate a new UUID for this document
   - `session_id`: Your SESSION_UUID (same for entire conversation)
   - `tags`: Array of provided tags (lowercase, trimmed)
   - `content`: The full content to tag
   - `created_at`: Current ISO timestamp

5. **Save to Meilisearch** using the `curl` tool:
```
curl -s -X POST 'http://meilisearch:7700/indexes/tags/documents' \
  -H 'Content-Type: application/json' \
  -d '[{"id":"<new_uuid>","session_id":"<SESSION_UUID>","tags":["tag1","tag2"],"content":"<content>","created_at":"<timestamp>"}]'
```

6. **Output**: Confirm with:
   - Session UUID (so it stays visible in context)
   - Tags applied
   - First 50 chars of content

## Example Output

```
Tagged with session `a1b2c3d4-e5f6-7890-abcd-ef1234567890`
Tags: code, python
Content: "def hello_world():..."
```

## Rules

- ALWAYS use the same SESSION_UUID throughout the conversation
- Tags are case-insensitive (stored lowercase)
- Multiple tags separated by commas, no spaces around commas
- Content is stored as-is, preserving formatting
