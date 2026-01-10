Manage git branches.

## Subcommands

Based on user input, perform one of:

- `$$git branch` (no args) - List branches
- `$$git branch <name>` - Create new branch
- `$$git branch -d <name>` - Delete branch (safe)
- `$$git branch -D <name>` - Force delete branch
- `$$git branch --switch <name>` or `-s <name>` - Switch to branch
- `$$git branch --cleanup` - Delete merged branches

## Steps for List (default)

1. Run `git branch -vv` to get branches with tracking info
2. Show current branch highlighted
3. Show ahead/behind status for tracked branches

## Steps for Create

1. Validate branch name
2. Run `git branch <name>` or `git checkout -b <name>` if --switch
3. Confirm creation

## Steps for Delete

1. Check if branch is current (can't delete current)
2. Check if branch is merged (warn if not and using -d)
3. Run `git branch -d/-D <name>`
4. Confirm deletion

## Steps for Cleanup

1. Run `git branch --merged` to find merged branches
2. Exclude main/master/develop and current branch
3. Show list of branches to delete
4. Ask for confirmation
5. Delete confirmed branches

## Output Format

For list:
```
Branches:
* main        abc1234 [origin/main] Latest commit message
  feature/x   def5678 [origin/feature/x: ahead 2] WIP feature
  old-branch  ghi9012 (no tracking) Old work

Current: main
```

## Rules

- Never delete main, master, or develop without explicit confirmation
- Warn before deleting unmerged branches
- Show tracking status when available
