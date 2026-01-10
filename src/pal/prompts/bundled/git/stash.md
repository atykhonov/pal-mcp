Manage git stashes interactively.

## Subcommands

Based on user input, perform one of:

- `$$git stash` (no args) - Stash current changes
- `$$git stash list` - List all stashes
- `$$git stash show [n]` - Show stash contents
- `$$git stash pop [n]` - Apply and remove stash
- `$$git stash apply [n]` - Apply but keep stash
- `$$git stash drop [n]` - Delete a stash
- `$$git stash clear` - Delete all stashes (ask confirmation!)

## Steps for Default (stash)

1. Check if there are changes to stash (`git status --short`)
2. If no changes, inform user and stop
3. Ask for optional stash message
4. Run `git stash push -m "message"` or just `git stash`
5. Confirm what was stashed

## Steps for List

1. Run `git stash list`
2. Format output nicely with index numbers
3. Show brief summary of each stash

## Output Format

For list:
```
Stashes:
  [0] 2 hours ago: WIP on main - feat: new feature
  [1] 1 day ago: WIP on main - fixing bug
  [2] 3 days ago: experimenting with API

Use `$$git stash show 0` to see contents
Use `$$git stash pop 0` to apply and remove
```

For stash/pop/apply:
```
Stashed changes from 3 files.
```

## Rules

- Always confirm before `stash clear`
- Show what will be affected before destructive operations
- Default to stash index 0 if not specified
- Include untracked files hint: use `-u` flag
