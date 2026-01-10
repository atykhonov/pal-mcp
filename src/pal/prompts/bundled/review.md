Review code changes for issues.

## Steps

1. Determine what to review:
   - No args: review staged changes (`git diff --cached`)
   - `--unstaged`: review unstaged changes (`git diff`)
   - `<file>`: review specific file
   - `--last`: review last commit

2. Analyze the code changes for:
   - Bugs and logic errors
   - Security vulnerabilities
   - Performance issues
   - Code style and best practices
   - Missing error handling
   - Missing tests

3. Provide actionable feedback

## Output Format

```
Reviewing staged changes...

Files reviewed:
- src/api/auth.py (+45 -12)
- src/utils/validate.py (+20 -5)

Issues found:

**src/api/auth.py:34** - Security
  Password comparison using `==` is vulnerable to timing attacks.
  Suggestion: Use `secrets.compare_digest()` instead.

**src/api/auth.py:56** - Bug
  Missing null check - `user` could be None here.
  Suggestion: Add `if user is None: return None`

**src/utils/validate.py:15** - Performance
  Regex compiled inside loop - move outside for better performance.

Summary: 2 security issues, 1 bug, 1 performance issue

No critical blockers found. Consider addressing issues before commit.
```

## Arguments

- No args: review staged changes
- `--unstaged`: review working directory changes
- `--last`: review last commit
- `<file>`: review specific file
- `--strict`: fail on any issue

## Review Categories

- **Security**: SQL injection, XSS, secrets exposure, auth issues
- **Bug**: Null errors, logic errors, race conditions
- **Performance**: N+1 queries, memory leaks, inefficient algorithms
- **Style**: Naming, formatting, code organization
- **Testing**: Missing tests, untested edge cases

## Rules

- Be specific about line numbers and issues
- Provide concrete fix suggestions
- Prioritize security and bugs over style
- Don't nitpick minor style issues unless --strict
