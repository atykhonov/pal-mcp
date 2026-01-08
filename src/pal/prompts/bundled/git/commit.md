Create conventional commits.

## Steps

1. Run `git status` to check for staged changes
2. If nothing staged, inform user and stop
3. Run `git diff --cached` to analyze changes
4. Create commit message following the rules below

## Commit Format

```
type(scope): subject line (max 72 chars)

Optional body explaining *why*, not *what*.
```

**Types:** feat, fix, docs, style, refactor, test, chore
**Style:** Imperative mood ("add" not "added"), no period at end

## Example

```
refactor(auth): extract token validation into separate module

Improves testability and allows reuse in API middleware.
```

## Rules

- DO NOT add AI attribution, co-authored-by lines, or emoji (unless asked)
- If user provides a description, use it
- If no description, analyze staged changes and create appropriate message
