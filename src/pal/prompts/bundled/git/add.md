Stage files for commit.

## Steps

1. Run `git status --porcelain` to get list of unstaged/untracked files
2. If no files to add, inform user and stop
3. Show the list of files that will be staged
4. Ask user to confirm: "Stage these files? (y/n)"
5. If confirmed, run `git add` on all listed files
6. Show confirmation of what was staged

## Status Codes

From `git status --porcelain`:
- ` M` = Modified (unstaged)
- `??` = Untracked (new file)
- ` D` = Deleted (unstaged)

Focus on files with changes in the second column (unstaged) and `??` (untracked).

## Output Format

```
Files to stage:
- path/to/modified.py (modified)
- path/to/new.py (new file)
- path/to/deleted.py (deleted)

Stage these files? (y/n)
```

After confirmation:
```
Staged N file(s).
```
