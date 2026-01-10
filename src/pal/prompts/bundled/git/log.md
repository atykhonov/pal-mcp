Show git log with formatting and filtering.

## Arguments

- No args: show recent commits (default 10)
- `-n <N>`: show N commits
- `--author <name>`: filter by author
- `--since <date>`: commits after date (e.g., "1 week ago", "2024-01-01")
- `--until <date>`: commits before date
- `--search <text>`: search commit messages
- `--file <path>`: commits touching file/path
- `--oneline`: compact one-line format

## Steps

1. Build git log command based on arguments
2. Run with pretty format
3. Display formatted output

## Output Format

Default format:
```
Recent commits (showing 10):

abc1234 - 2 hours ago
  feat(auth): add OAuth support
  Author: John Doe <john@example.com>

def5678 - 1 day ago
  fix(api): handle null response
  Author: Jane Smith <jane@example.com>

[... more commits ...]

Use `$$git log -n 20` to see more
Use `$$git log --author "John"` to filter by author
```

Oneline format:
```
abc1234 feat(auth): add OAuth support (2 hours ago)
def5678 fix(api): handle null response (1 day ago)
ghi9012 docs: update README (3 days ago)
```

## Rules

- Default to 10 commits if no count specified
- Show relative dates by default
- Include author info in default view
- Provide hints for filtering options
