Stage files for commit.

## Steps

1. Run `git status --porcelain` to get list of unstaged/untracked files
2. If no files to add, inform user and stop
3. For each file with changes:
   - Run `git diff <filename>` to get the diff
   - Display the diff in your response as a markdown code block (so user sees it directly)
   - Run `git add <filename>` (Claude Code will ask for permission)
4. After all files processed, show summary of what was staged

**Important**: Always display the diff content directly in your response text using a ```diff code block. Do not rely on command output being visible.

## Status Codes

From `git status --porcelain`:
- ` M` = Modified (unstaged)
- `??` = Untracked (new file)
- ` D` = Deleted (unstaged)

Focus on files with changes in the second column (unstaged) and `??` (untracked).

## Output Format

For each file, show the diff then stage:

**1/N: path/to/file.ext** (modified)

```diff
[git diff output]
```

Then run `git add` for that file.

Final summary:
```
Staged N file(s):
- file1.ext
- file2.ext

Skipped M file(s) (user declined):
- file3.ext
```
