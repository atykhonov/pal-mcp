Show and summarize git diffs.

## Steps

1. Determine what to diff:
   - No args: show unstaged changes (`git diff`)
   - `--staged` or `--cached`: show staged changes (`git diff --cached`)
   - File path: show diff for specific file
2. Run the appropriate git diff command
3. Present the diff with summary

## Output Format

For small diffs (< 100 lines), show the full diff:

```diff
[full diff output]
```

For large diffs, show a summary first:

```
Summary: 5 files changed, +150 -45 lines

Files modified:
- src/main.py (+50 -10) - Added new API endpoints
- src/utils.py (+30 -5) - Refactored helper functions
- tests/test_main.py (+70 -30) - Updated tests
```

Then offer to show full diff for specific files.

## Arguments

- No args: unstaged changes
- `--staged` / `--cached`: staged changes
- `<file>`: specific file
- `<commit>`: changes since commit
- `<commit1>..<commit2>`: changes between commits

## Rules

- For large diffs, summarize what changed in each file
- Use `<details>` blocks for long diffs
- Highlight important changes (new functions, deleted code, etc.)
- Suggest next actions based on what's shown
