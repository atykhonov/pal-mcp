Auto-fix code issues.

## Steps

1. Detect the project type and available fixers:
   - `pyproject.toml` / `setup.py` -> ruff, black, isort, autopep8
   - `package.json` -> eslint --fix, prettier, npm run lint:fix
   - `Cargo.toml` -> cargo fmt, cargo clippy --fix
   - `go.mod` -> gofmt, goimports
   - `.clang-format` -> clang-format
   - `Makefile` with lint-fix/format target -> make lint-fix/format

2. Determine what to fix:
   - No args: fix all files (or staged files if any)
   - File path: fix specific file
   - `--staged`: fix only staged files
   - `--check`: show what would be fixed without applying

3. Run the appropriate fixer(s)

4. Show summary of changes

## Output Format

```
Detected: Python project with ruff, black

Running fixers...

ruff check --fix:
  Fixed 3 issues in src/api/auth.py
  Fixed 1 issue in src/utils/helpers.py

black:
  Reformatted src/api/auth.py
  Reformatted src/models/user.py

Summary:
- 4 linting issues fixed
- 2 files reformatted

Run `git diff` to review changes
```

## Arguments

- No args: fix all (or staged files)
- `<path>`: fix specific file/directory
- `--staged`: fix only staged files
- `--check` / `--dry-run`: show what would be fixed
- `--type <linter>`: use specific fixer (ruff, eslint, etc.)

## Supported Fixers

**Python:**
- ruff check --fix (linting)
- ruff format (formatting)
- black (formatting)
- isort (import sorting)

**JavaScript/TypeScript:**
- eslint --fix
- prettier --write
- npm run lint:fix (if available)

**Rust:**
- cargo fmt
- cargo clippy --fix --allow-dirty

**Go:**
- gofmt -w
- goimports -w

## Rules

- Auto-detect available fixers from project config
- Run multiple fixers in correct order (lint before format)
- Show clear summary of what was fixed
- Support --check mode for CI/preview
- Don't modify files outside the project directory
