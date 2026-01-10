Safely undo git operations.

## Subcommands

Based on user input, perform one of:

- `$$git undo` (no args) - Show undo options based on current state
- `$$git undo staged` - Unstage all staged files
- `$$git undo staged <file>` - Unstage specific file
- `$$git undo changes <file>` - Discard changes in file (DESTRUCTIVE)
- `$$git undo commit` - Undo last commit, keep changes staged
- `$$git undo commit --hard` - Undo last commit and discard changes (DESTRUCTIVE)

## Steps for Default (no args)

1. Check current state with `git status`
2. Check last commit with `git log -1`
3. Show relevant undo options based on state

## Steps for Unstage

1. Run `git restore --staged <file>` or `git restore --staged .`
2. Confirm what was unstaged

## Steps for Discard Changes

1. WARN user this is destructive
2. Show what will be lost (diff)
3. Ask for confirmation
4. Run `git restore <file>` or `git checkout -- <file>`

## Steps for Undo Commit

1. Check if commit has been pushed (warn if yes)
2. Show commit that will be undone
3. Ask for confirmation
4. Run `git reset --soft HEAD~1` (or --hard if requested)

## Output Format

For default:
```
Current state:
- 2 staged files
- 3 unstaged changes
- Last commit: abc1234 "feat: add feature" (2 hours ago, not pushed)

Available undo options:
- `$$git undo staged` - Unstage all files
- `$$git undo changes src/file.py` - Discard changes in file
- `$$git undo commit` - Undo last commit (keep changes)
```

## Rules

- ALWAYS warn before destructive operations
- Show what will be affected before doing anything
- Check if commits are pushed before allowing undo
- Default to safe operations (--soft, not --hard)
- Never force-push without explicit user request
