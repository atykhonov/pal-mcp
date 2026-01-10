Run tests intelligently.

## Steps

1. Detect the test framework by checking for:
   - `pytest.ini`, `pyproject.toml` with pytest config, `conftest.py` -> pytest
   - `package.json` with jest/mocha/vitest -> npm test / npx jest/vitest
   - `Cargo.toml` -> cargo test
   - `go.mod` -> go test ./...
   - `Makefile` with test target -> make test

2. Determine what to test:
   - No args: run all tests
   - File path: run tests in that file
   - `-f` / `--failed`: re-run failed tests only
   - `-r` / `--related`: run tests related to changed files
   - Search term: run tests matching pattern

3. Run the tests and capture output

4. If tests fail:
   - Show clear summary of failures
   - Offer to fix failures

## Output Format

```
Detected: pytest

Running: pytest tests/ -v

... [test output] ...

Results: 45 passed, 2 failed, 1 skipped

Failed tests:
1. tests/test_api.py::test_login_invalid
   AssertionError: Expected 401, got 500

2. tests/test_utils.py::test_parse_date
   ValueError: Invalid date format

Run `$$fix tests/test_api.py` to attempt auto-fix
```

## Arguments

- No args: run all tests
- `<path>`: run tests in file/directory
- `-f` / `--failed`: re-run only failed tests
- `-r` / `--related`: run tests for changed files
- `-v` / `--verbose`: verbose output
- `<pattern>`: run tests matching pattern

## Rules

- Auto-detect test framework from project files
- Show clear pass/fail summary
- On failure, show actionable next steps
- Support common test frameworks
