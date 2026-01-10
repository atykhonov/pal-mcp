Show git status with actionable suggestions.

## Steps

1. Run `git status --short --branch` to get current state
2. Parse and categorize the changes
3. Display a formatted summary with suggestions

## Output Format

```
Branch: main (ahead 2, behind 1)

Staged (ready to commit):
  M  src/file.py
  A  src/new.py

Unstaged changes:
  M  src/other.py
  D  src/deleted.py

Untracked files:
  ??  src/untracked.py

Suggestions:
- Run `$$git commit` to commit staged changes
- Run `$$git add` to stage unstaged changes
- Run `$$git stash` to stash changes before pulling
```

## Status Codes

- `M` = Modified
- `A` = Added
- `D` = Deleted
- `R` = Renamed
- `C` = Copied
- `??` = Untracked
- `!!` = Ignored

First column = staged, second column = unstaged.

## Rules

- Always show branch info with ahead/behind if available
- Group files by category (staged, unstaged, untracked)
- Provide relevant suggestions based on current state
- If working tree is clean, say so clearly
