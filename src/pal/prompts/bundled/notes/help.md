Show available notes commands.

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
