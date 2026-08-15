# Pipeline Grammar Ownership — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `parse_pipeline` MCP tool that owns pipeline tokenization in Python, and make `run_pal_command` reject pipeline strings so callers must route through it — eliminating the cold-start failure where built-in commands (`$$echo`, `$$prompt`, `$$help`) never receive `root.md`'s pipeline rules.

**Architecture:** A new `src/pal/tools/pipeline.py` module owns the tokenizer (left-to-right scan, ` -- ` raw-mode edge marker, space-surrounded ` | `/` && `/` ; ` operators, no quoting). The tokenizer is exposed both as an MCP tool (`parse_pipeline`) returning JSON stages, and as an internal `is_pipeline()` guard used inside `run_pal_command` to reject multi-stage input with an LLM-directed error message. The pipeline section of `root.md` is stripped because the `parse_pipeline` tool description becomes the single source of truth.

**Tech Stack:** Python 3.12+, FastMCP (`mcp.server.fastmcp`), pytest, pytest-asyncio (`asyncio_mode = "auto"`), black, ruff, mypy (strict).

**Reference brief:** [`docs/plans/2026-05-16-pipeline-grammar-ownership.md`](2026-05-16-pipeline-grammar-ownership.md).

---

## File Structure

**New files:**

- `src/pal/tools/pipeline.py` — `PipelineStage` dataclass, `tokenize_pipeline()` function, `is_pipeline()` helper. Single responsibility: turn a raw command string into a structured list of stages.
- `tests/test_pipeline.py` — unit tests for tokenizer covering every case in the brief's verification list.

**Modified files:**

- `src/pal/tools/registry.py` — register a new `parse_pipeline` MCP tool that wraps the tokenizer and returns JSON; gate `run_pal_command` to reject inputs that contain pipeline operators.
- `src/pal/prompts/bundled/root.md` — remove the "Pipeline Operators" section (currently lines 24-41), since the `parse_pipeline` tool description is now canonical.
- `tests/test_registry.py` — assert `parse_pipeline` is registered with the expected schema; assert `run_pal_command` rejects pipeline strings with the documented error.

**Why this split:** `pipeline.py` is intentionally separate from the existing `parser.py`. `parser.py` extracts the namespace from a single command; `pipeline.py` decomposes a chain of commands. Different responsibility, different test surface — keeping them separate keeps each file small enough to hold in one context.

---

## Conventions

**Code style:** All files start with `from __future__ import annotations`. Use `dataclass(frozen=True, slots=True)` for value types (matches `ParsedCommand` in `src/pal/tools/parser.py:8`).

**Test style:** pytest classes named `TestX`. `asyncio_mode = "auto"` is set in `pyproject.toml` so `async def test_*` works without decorators. Sync tests for the pure tokenizer.

**Commit style:** Conventional commits matching repo history — `feat(tools):`, `refactor(tools):`, `chore:`, `docs:`, etc. See `git log --oneline -10` for examples.

**Run order between tasks:** Always run the full suite at the end of each task, not just the new tests, to catch regressions in `test_registry.py` and elsewhere.

---

## Task 1: Bootstrap the pipeline module with a single-stage parse

Defines the data shape and gets a passing test through the simplest possible input. No operator handling yet.

**Files:**
- Create: `src/pal/tools/pipeline.py`
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_pipeline.py`:

```python
"""Tests for pipeline tokenization."""

from __future__ import annotations

from pal.tools.pipeline import PipelineStage, tokenize_pipeline


class TestTokenizeSingleStage:
    """No pipeline operators present — one stage, no operator."""

    def test_simple_command(self) -> None:
        stages = tokenize_pipeline("echo hello")
        assert stages == [PipelineStage(cmd="echo hello", op=None)]

    def test_empty_string(self) -> None:
        assert tokenize_pipeline("") == []

    def test_whitespace_only(self) -> None:
        assert tokenize_pipeline("   ") == []

    def test_outer_whitespace_stripped(self) -> None:
        stages = tokenize_pipeline("  echo hello  ")
        assert stages == [PipelineStage(cmd="echo hello", op=None)]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pipeline.py -v`
Expected: `ModuleNotFoundError: No module named 'pal.tools.pipeline'` (or `ImportError`).

- [ ] **Step 3: Write minimal implementation**

Create `src/pal/tools/pipeline.py`:

```python
"""Pipeline tokenization for $$commands.

Owns the single source of truth for PAL's pipeline grammar:
left-to-right scan; ` -- ` (space-dash-dash-space) starts raw mode and
halts further tokenization; the operators ` | `, ` && `, and ` ; ` are
recognised only when space-surrounded. There are no escape sequences
and no quoting — anything that needs to contain operator-shaped bytes
goes after a ` -- ` edge marker.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PipelineStage:
    """One stage of a pipeline.

    `cmd` is the stage text with no surrounding whitespace.
    `op` is the operator joining this stage to the *next* stage, or
    None for the final stage (or for a single-stage command).
    """

    cmd: str
    op: str | None


def tokenize_pipeline(command: str) -> list[PipelineStage]:
    """Tokenize a $$command string into pipeline stages.

    Returns an empty list if `command` is empty or whitespace-only.
    See module docstring for the grammar.
    """
    text = command.strip()
    if not text:
        return []
    return [PipelineStage(cmd=text, op=None)]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pipeline.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/pal/tools/pipeline.py tests/test_pipeline.py
git commit -m "feat(tools): scaffold pipeline tokenizer with single-stage parsing"
```

---

## Task 2: Recognise the three pipeline operators

Add operator detection. `--` handling comes in Task 3 — the tests in this task deliberately avoid `--` so we can implement a naive scan first.

**Files:**
- Modify: `src/pal/tools/pipeline.py`
- Modify: `tests/test_pipeline.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_pipeline.py`:

```python
class TestTokenizeOperators:
    """Each operator splits the command at the operator location."""

    def test_pipe(self) -> None:
        stages = tokenize_pipeline("echo hello | tr")
        assert stages == [
            PipelineStage(cmd="echo hello", op="|"),
            PipelineStage(cmd="tr", op=None),
        ]

    def test_and(self) -> None:
        stages = tokenize_pipeline("foo && bar")
        assert stages == [
            PipelineStage(cmd="foo", op="&&"),
            PipelineStage(cmd="bar", op=None),
        ]

    def test_seq(self) -> None:
        stages = tokenize_pipeline("foo ; bar")
        assert stages == [
            PipelineStage(cmd="foo", op=";"),
            PipelineStage(cmd="bar", op=None),
        ]

    def test_three_stage_pipe(self) -> None:
        stages = tokenize_pipeline("a | b | c")
        assert stages == [
            PipelineStage(cmd="a", op="|"),
            PipelineStage(cmd="b", op="|"),
            PipelineStage(cmd="c", op=None),
        ]

    def test_mixed_operators(self) -> None:
        stages = tokenize_pipeline("a && b ; c")
        assert stages == [
            PipelineStage(cmd="a", op="&&"),
            PipelineStage(cmd="b", op=";"),
            PipelineStage(cmd="c", op=None),
        ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_pipeline.py::TestTokenizeOperators -v`
Expected: 5 failures (single-stage impl returns the whole string as one stage).

- [ ] **Step 3: Implement operator scanning**

Replace the body of `tokenize_pipeline` in `src/pal/tools/pipeline.py`:

```python
_OPERATORS: tuple[str, ...] = (" && ", " | ", " ; ")
# Order matters: ` && ` must be checked before ` & ` would be (we don't
# recognise ` & ` today; this just documents the lookup-order intent if
# more operators are added).


def tokenize_pipeline(command: str) -> list[PipelineStage]:
    """Tokenize a $$command string into pipeline stages.

    Returns an empty list if `command` is empty or whitespace-only.
    See module docstring for the grammar.
    """
    text = command.strip()
    if not text:
        return []

    stages: list[PipelineStage] = []
    cursor = 0
    while cursor < len(text):
        next_op_index = -1
        next_op: str | None = None
        for op in _OPERATORS:
            idx = text.find(op, cursor)
            if idx == -1:
                continue
            if next_op_index == -1 or idx < next_op_index:
                next_op_index = idx
                next_op = op
        if next_op is None:
            stages.append(PipelineStage(cmd=text[cursor:].strip(), op=None))
            break
        stage_text = text[cursor:next_op_index].strip()
        stages.append(PipelineStage(cmd=stage_text, op=next_op.strip()))
        cursor = next_op_index + len(next_op)
    return stages
```

`★ Insight ─────────────────────────────────────`
`find()` returns the earliest match of each operator from `cursor`, and we pick the smallest of those — that's a left-to-right scan in O(n·k) where k is the number of operator kinds (3). It's not the fastest possible (Aho-Corasick would be O(n)), but command strings are short and k is tiny, so the simpler code wins.
`─────────────────────────────────────────────────`

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_pipeline.py -v`
Expected: all 9 tests passing (4 from Task 1 + 5 from Task 2).

- [ ] **Step 5: Commit**

```bash
git add src/pal/tools/pipeline.py tests/test_pipeline.py
git commit -m "feat(tools): recognise pipeline operators in tokenizer"
```

---

## Task 3: Honor the ` -- ` raw-mode edge marker

Once ` -- ` (space-dash-dash-space) is seen, the rest of the string is one opaque stage. This task adds the rule and the regression tests showing that operators *after* `--` are not recognised, and that `--` without spaces (e.g. `--help`) is *not* the edge marker.

**Files:**
- Modify: `src/pal/tools/pipeline.py`
- Modify: `tests/test_pipeline.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_pipeline.py`:

```python
class TestRawModeEdgeMarker:
    """` -- ` (space-dash-dash-space) starts raw mode for the remainder."""

    def test_double_dash_suppresses_pipe(self) -> None:
        stages = tokenize_pipeline("tr -- hello | world")
        assert stages == [PipelineStage(cmd="tr -- hello | world", op=None)]

    def test_double_dash_suppresses_all_operators(self) -> None:
        stages = tokenize_pipeline("cmd -- a | b && c ; d")
        assert stages == [PipelineStage(cmd="cmd -- a | b && c ; d", op=None)]

    def test_second_double_dash_is_payload(self) -> None:
        stages = tokenize_pipeline("cmd -- foo -- bar | baz")
        assert stages == [PipelineStage(cmd="cmd -- foo -- bar | baz", op=None)]

    def test_operator_before_double_dash_still_splits(self) -> None:
        stages = tokenize_pipeline("a | tr -- hello | world")
        assert stages == [
            PipelineStage(cmd="a", op="|"),
            PipelineStage(cmd="tr -- hello | world", op=None),
        ]

    def test_double_dash_without_spaces_is_not_edge_marker(self) -> None:
        # `--help` is a flag, not a raw-mode marker (no leading space).
        stages = tokenize_pipeline("echo --help")
        assert stages == [PipelineStage(cmd="echo --help", op=None)]

    def test_unicode_payload_passes_through(self) -> None:
        stages = tokenize_pipeline("tr -- 你好 | мир 🌍")
        assert stages == [PipelineStage(cmd="tr -- 你好 | мир 🌍", op=None)]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_pipeline.py::TestRawModeEdgeMarker -v`
Expected: at least the four `--`-affected tests fail (the naive scan splits on `|` after `--`). The `--help` test may already pass since `--help` has no leading space — confirm it does.

- [ ] **Step 3: Implement the edge marker**

In `src/pal/tools/pipeline.py`, add a module-level constant and use it to bound the scan:

```python
_RAW_EDGE_MARKER = " -- "
```

Then update `tokenize_pipeline` to find the raw-mode boundary once, up front, and cap the operator search at that index:

```python
def tokenize_pipeline(command: str) -> list[PipelineStage]:
    """Tokenize a $$command string into pipeline stages.

    Returns an empty list if `command` is empty or whitespace-only.
    See module docstring for the grammar.
    """
    text = command.strip()
    if not text:
        return []

    raw_boundary = text.find(_RAW_EDGE_MARKER)
    scan_limit = raw_boundary if raw_boundary != -1 else len(text)

    stages: list[PipelineStage] = []
    cursor = 0
    while cursor < len(text):
        next_op_index = -1
        next_op: str | None = None
        for op in _OPERATORS:
            idx = text.find(op, cursor)
            if idx == -1 or idx >= scan_limit:
                continue
            if next_op_index == -1 or idx < next_op_index:
                next_op_index = idx
                next_op = op
        if next_op is None:
            stages.append(PipelineStage(cmd=text[cursor:].strip(), op=None))
            break
        stage_text = text[cursor:next_op_index].strip()
        stages.append(PipelineStage(cmd=stage_text, op=next_op.strip()))
        cursor = next_op_index + len(next_op)
    return stages
```

`★ Insight ─────────────────────────────────────`
The boundary check uses `idx >= scan_limit` (not `>`), so an operator whose first character is *at* the start of the raw marker is also excluded. The raw marker itself starts with a space, so any ` | `, ` && `, or ` ; ` operator *inside* the `-- payload` lies strictly after `scan_limit` and is skipped. The final-stage branch (`if next_op is None`) then sweeps everything from `cursor` to end of string into one stage, which is exactly what raw mode requires.
`─────────────────────────────────────────────────`

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_pipeline.py -v`
Expected: all 15 tests passing.

- [ ] **Step 5: Commit**

```bash
git add src/pal/tools/pipeline.py tests/test_pipeline.py
git commit -m "feat(tools): honor ` -- ` raw-mode edge marker in tokenizer"
```

---

## Task 4: Cover the remaining grammar corner cases from the brief

These are the cases the brief explicitly calls out: no-space-around-operator must not split; `||` must not split (no ` | ` substring); `$` and other punctuation are opaque. They're tests against the existing implementation, not new features — but they lock down the grammar.

**Files:**
- Modify: `tests/test_pipeline.py`

- [ ] **Step 1: Write the failing (or already-passing) tests**

Append to `tests/test_pipeline.py`:

```python
class TestGrammarCornerCases:
    """Edge cases that should NOT split on operators."""

    def test_pipe_without_spaces_is_one_stage(self) -> None:
        stages = tokenize_pipeline("echo a|b")
        assert stages == [PipelineStage(cmd="echo a|b", op=None)]

    def test_double_pipe_is_opaque(self) -> None:
        # `||` contains no ` | ` substring (no space-pipe-space anywhere).
        stages = tokenize_pipeline("a || b")
        assert stages == [PipelineStage(cmd="a || b", op=None)]

    def test_amp_without_spaces_is_one_stage(self) -> None:
        stages = tokenize_pipeline("foo&&bar")
        assert stages == [PipelineStage(cmd="foo&&bar", op=None)]

    def test_dollar_var_is_opaque(self) -> None:
        # Variable substitution stays LLM-side; $5 is just text here.
        stages = tokenize_pipeline("echo $5 && cat")
        assert stages == [
            PipelineStage(cmd="echo $5", op="&&"),
            PipelineStage(cmd="cat", op=None),
        ]

    def test_url_query_string_is_opaque(self) -> None:
        stages = tokenize_pipeline("curl https://x.test?foo&bar | jq")
        assert stages == [
            PipelineStage(cmd="curl https://x.test?foo&bar", op="|"),
            PipelineStage(cmd="jq", op=None),
        ]

    def test_realistic_notes_pipeline(self) -> None:
        stages = tokenize_pipeline("notes search docker | summarize")
        assert stages == [
            PipelineStage(cmd="notes search docker", op="|"),
            PipelineStage(cmd="summarize", op=None),
        ]
```

- [ ] **Step 2: Run tests to verify all pass without code changes**

Run: `pytest tests/test_pipeline.py -v`
Expected: all 21 tests passing. If any fail, the tokenizer has a bug that escaped Tasks 1-3 — fix it before continuing.

`★ Insight ─────────────────────────────────────`
These tests look redundant with Task 2, but they exist for a specific reason: they're the cases brief readers will be most likely to question ("does `||` really not split?"). Locking them in tests turns prose claims into machine-verified guarantees, which is the whole point of moving grammar out of `root.md`.
`─────────────────────────────────────────────────`

- [ ] **Step 3: Commit**

```bash
git add tests/test_pipeline.py
git commit -m "test(tools): lock in pipeline grammar corner cases"
```

---

## Task 5: Add the `is_pipeline` helper for the `run_pal_command` guard

`run_pal_command` needs to detect "this string contains operators" without building the full stage list. Define a lightweight helper for that, with its own tests. It reuses the same scan rules so the guard is provably consistent with the tokenizer.

**Files:**
- Modify: `src/pal/tools/pipeline.py`
- Modify: `tests/test_pipeline.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_pipeline.py`:

```python
from pal.tools.pipeline import is_pipeline  # add at top of file


class TestIsPipeline:
    """is_pipeline mirrors tokenize_pipeline's operator detection."""

    def test_single_stage_is_not_pipeline(self) -> None:
        assert is_pipeline("echo hello") is False

    def test_empty_is_not_pipeline(self) -> None:
        assert is_pipeline("") is False

    def test_pipe_is_pipeline(self) -> None:
        assert is_pipeline("a | b") is True

    def test_and_is_pipeline(self) -> None:
        assert is_pipeline("a && b") is True

    def test_seq_is_pipeline(self) -> None:
        assert is_pipeline("a ; b") is True

    def test_raw_mode_suppresses_detection(self) -> None:
        assert is_pipeline("tr -- a | b") is False

    def test_no_spaces_around_operator_is_not_pipeline(self) -> None:
        assert is_pipeline("a|b") is False

    def test_double_pipe_is_not_pipeline(self) -> None:
        assert is_pipeline("a || b") is False
```

(The `from pal.tools.pipeline import is_pipeline` line goes at the top of the file alongside the existing import — combine them into one line.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_pipeline.py::TestIsPipeline -v`
Expected: `ImportError: cannot import name 'is_pipeline'`.

- [ ] **Step 3: Implement `is_pipeline`**

Append to `src/pal/tools/pipeline.py`:

```python
def is_pipeline(command: str) -> bool:
    """Return True if `command` contains a pipeline operator outside raw mode.

    Uses the same scan rules as tokenize_pipeline so the two cannot drift.
    Avoids building the full stage list — useful as a cheap guard.
    """
    text = command.strip()
    if not text:
        return False
    raw_boundary = text.find(_RAW_EDGE_MARKER)
    scan_limit = raw_boundary if raw_boundary != -1 else len(text)
    for op in _OPERATORS:
        idx = text.find(op)
        if idx != -1 and idx < scan_limit:
            return True
    return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_pipeline.py -v`
Expected: all 29 tests passing.

- [ ] **Step 5: Commit**

```bash
git add src/pal/tools/pipeline.py tests/test_pipeline.py
git commit -m "feat(tools): add is_pipeline helper for run_pal_command guard"
```

---

## Task 6: Register `parse_pipeline` as an MCP tool

Wrap `tokenize_pipeline` as an MCP tool returning JSON. The tool description is the canonical grammar reference for the LLM — write it carefully.

**Files:**
- Modify: `src/pal/tools/registry.py`
- Modify: `tests/test_registry.py`

- [ ] **Step 1: Write the failing tests**

In `tests/test_registry.py`, update the expected tool set and add new schema tests. Replace the body of `test_all_tools_registered` and append two new tests:

```python
    def test_all_tools_registered(self) -> None:
        """All 6 tools are registered."""
        tool_names = set(mcp._tool_manager._tools)
        expected = {
            "run_pal_command",
            "list_pal_commands",
            "read_pal_resource",
            "list_pal_resources",
            "pal_curl",
            "parse_pipeline",
        }
        assert expected == tool_names

    def test_parse_pipeline_schema(self) -> None:
        """parse_pipeline has required `command` string parameter."""
        tool = mcp._tool_manager._tools["parse_pipeline"]
        schema = tool.parameters
        assert "command" in schema.get("properties", {})
        assert "command" in schema.get("required", [])

    def test_parse_pipeline_description_documents_grammar(self) -> None:
        """parse_pipeline's description names every operator and the `--` marker.

        This is the *canonical* grammar reference exposed to the LLM, so the
        description must mention each piece — otherwise the LLM can't apply
        the rules.
        """
        tool = mcp._tool_manager._tools["parse_pipeline"]
        description = (tool.description or "").lower()
        for token in ("|", "&&", ";", "--"):
            assert token in description, f"missing {token!r} in description"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_registry.py -v`
Expected: `test_all_tools_registered`, `test_parse_pipeline_schema`, `test_parse_pipeline_description_documents_grammar` all fail (tool not registered yet).

- [ ] **Step 3: Register the tool**

In `src/pal/tools/registry.py`, add the import and the new tool. Update imports near the top:

```python
import json

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from pal.config import get_settings
from pal.prompts import (
    list_available_commands,
    list_custom_prompts,
    load_custom_prompt,
    load_prompt,
)
from pal.tools.curl import execute_curl
from pal.tools.handlers import execute_command
from pal.tools.parser import parse_command
from pal.tools.pipeline import tokenize_pipeline
```

Append the new tool *after* the existing `pal_curl` tool at the end of the file:

```python
@mcp.tool()
def parse_pipeline(command: str) -> str:
    """Tokenize a $$command containing pipeline operators into stages.

    Call this BEFORE run_pal_command whenever the user input may contain
    a pipeline. Returns a JSON array of stages:

      [{"cmd": "<text>", "op": "|" | "&&" | ";" | null}, ...]

    The `op` field is the operator joining this stage to the NEXT one;
    it is null on the final stage. Execute each stage by passing its
    `cmd` to run_pal_command, and when `op` is `|`, append the previous
    stage's output to the next stage's input.

    Grammar (single source of truth):
      - Operators are recognised only when space-surrounded:
        ` | ` (pipe), ` && ` (and), ` ; ` (seq).
      - The literal ` -- ` (space-dash-dash-space) starts raw mode:
        everything after it is one opaque stage, with no further
        operator recognition. Use ` -- ` whenever a command embeds
        free-form text (translations, summaries, search queries,
        user-provided content) to prevent accidental pipeline parsing.
        Example: `$$tr -- $MSG` not `$$tr $MSG`.
      - There is no quoting and no escape sequences. Anything that
        needs to contain operator-shaped bytes goes after ` -- `.
    """
    print("[TOOL] Executing parse_pipeline...")
    stages = tokenize_pipeline(command)
    payload = [{"cmd": s.cmd, "op": s.op} for s in stages]
    return json.dumps(payload)
```

`★ Insight ─────────────────────────────────────`
`@mcp.tool()` uses the function's docstring as the tool description that the LLM sees. The description here is intentionally long — it includes the *why* and an example — because this docstring is now the canonical grammar reference. Tests in step 1 mechanically verify the description still mentions every operator and the `--` marker, so future edits can't accidentally drop a rule.
`─────────────────────────────────────────────────`

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_registry.py -v`
Expected: all tests passing, including the new three.

- [ ] **Step 5: Commit**

```bash
git add src/pal/tools/registry.py tests/test_registry.py
git commit -m "feat(tools): expose parse_pipeline MCP tool with canonical grammar docs"
```

---

## Task 7: Reject pipeline strings in `run_pal_command`

Use `is_pipeline()` to guard `run_pal_command`. If a pipeline string slips through, return an LLM-directed error telling it exactly which tool to call next.

**Files:**
- Modify: `src/pal/tools/registry.py`
- Modify: `tests/test_registry.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_registry.py`. The file is under `asyncio_mode = "auto"` so `async def test_*` works without decorators. Note: FastMCP's `@mcp.tool()` returns the *original* function, so the module-level `run_pal_command` symbol is the plain async function — call it directly:

```python
from pal.tools.registry import run_pal_command


class TestRunPalCommandRejectsPipelines:
    """run_pal_command must refuse multi-stage strings and direct the
    caller (the LLM) to parse_pipeline first.

    We only assert against the rejection path (which never touches ctx),
    so passing ctx=None is safe — the guard fires before any ctx access.
    The "raw-mode commands are NOT rejected" case is covered by the
    is_pipeline unit tests in tests/test_pipeline.py (Task 5), so we
    don't repeat it here.
    """

    async def test_rejects_pipe(self) -> None:
        result = await run_pal_command(command="a | b", ctx=None)  # type: ignore[arg-type]
        assert "parse_pipeline" in result
        assert "pipeline" in result.lower()

    async def test_rejects_and(self) -> None:
        result = await run_pal_command(command="a && b", ctx=None)  # type: ignore[arg-type]
        assert "parse_pipeline" in result

    async def test_rejects_seq(self) -> None:
        result = await run_pal_command(command="a ; b", ctx=None)  # type: ignore[arg-type]
        assert "parse_pipeline" in result
```

`★ Insight ─────────────────────────────────────`
FastMCP's `@mcp.tool()` decorator (in mcp >=1.27.0) returns the original function unchanged — it registers the function with the tool manager as a side effect. The `Tool` object with `.fn`, `.parameters`, etc. lives only inside `mcp._tool_manager._tools[name]`, never replaces the module-level symbol. That makes unit-testing the guard trivial: just call `await run_pal_command(...)` like any async function.

These rejection tests also implicitly verify wiring: if the guard weren't wired into `run_pal_command`, the function would fall through to `ctx.request_context` on a `None` ctx and raise `AttributeError`, not return the documented error string. So one assertion exercises two properties — the guard fires *and* it's actually called.
`─────────────────────────────────────────────────`

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_registry.py::TestRunPalCommandRejectsPipelines -v`
Expected: all 5 rejection tests fail — the first three because the guard doesn't exist; the last two may already pass (no guard means no rejection) but will be verified by step 4.

- [ ] **Step 3: Add the guard**

In `src/pal/tools/registry.py`, add `is_pipeline` to the import and update `run_pal_command`:

```python
from pal.tools.pipeline import is_pipeline, tokenize_pipeline
```

Replace the body of `run_pal_command` (currently `src/pal/tools/registry.py:33-42`):

```python
@mcp.tool()
async def run_pal_command(command: str, ctx: Context) -> str:  # type: ignore[type-arg]
    """Execute a single PAL $$ command stage.

    For built-in commands (echo, prompt, help): executes and returns result.
    For prompt-based commands: returns bundled prompts for you to follow.

    Does NOT execute pipelines. If `command` contains a pipeline operator
    (` | `, ` && `, ` ; ` — space-surrounded, outside any ` -- ` raw region),
    this tool returns an error directing you to call parse_pipeline first
    and then call run_pal_command once per returned stage.
    """
    command = command.strip()
    if not command:
        return "Error: No command provided"

    if is_pipeline(command):
        return (
            "Error: Pipeline operators detected in command. "
            "Call parse_pipeline(command) first to split the string "
            "into stages, then call run_pal_command once per returned "
            "stage, passing the previous stage's output as the next "
            "stage's input when op == '|'. "
            "If the operator characters were meant literally, place "
            "the content at the end of the command after ` -- ` to "
            "activate raw mode and prevent operator parsing."
        )

    print("[TOOL] Executing run_pal_command...")
    parsed = parse_command(command)
    return await execute_command(parsed, ctx.request_context)
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `pytest -v`
Expected: full suite green. Pay attention to any pre-existing test in `tests/test_registry.py` that may have used pipeline-shaped commands.

- [ ] **Step 5: Commit**

```bash
git add src/pal/tools/registry.py tests/test_registry.py
git commit -m "feat(tools): reject pipeline strings in run_pal_command, directing to parse_pipeline"
```

---

## Task 8: Strip the now-redundant Pipeline Operators section from `root.md`

The `parse_pipeline` tool description (Task 6) is the canonical grammar reference. Remove the duplicate prose from `root.md` so a future grammar change has exactly one place to update. The rest of `root.md` is intentionally left for the separate [protocol-header-hoist brief](2026-05-16-protocol-header-hoist.md).

**Files:**
- Modify: `src/pal/prompts/bundled/root.md`

- [ ] **Step 1: Remove the "Pipeline Operators" section**

In `src/pal/prompts/bundled/root.md`, delete lines 24-41 inclusive — the entire `## Pipeline Operators` section, from its heading through the `--` paragraph ending in `everything after \`--\` is content.`. The result should jump directly from the closing of `## Variable Substitution` to the start of `## Executing Prompt-Based Commands`.

After the edit, `root.md` should read (showing the seam):

```markdown
## Variable Substitution

Available variables:
- `$MSG` - User's previous message
- `$REPLY` - Your previous response
- `$REPLY1`, `$REPLY2`, ... - Older responses (1 back, 2 back, etc.)
- `$REPLIES` - All your previous responses (concatenated)
- Heading variables: `## Summary` creates `$SUMMARY`

## Executing Prompt-Based Commands

When you receive bundled prompts (this response):
...
```

- [ ] **Step 2: Verify nothing else in the codebase still expects the section**

Run: `grep -rn "Pipeline Operators" src tests docs/plans`
Expected: no matches in `src/` or `tests/`. Matches in `docs/plans/` (the briefs) are fine — those are historical documents.

Also run: `grep -rn "root.md" src tests`
Expected: matches in `src/pal/tools/handlers.py` and `src/pal/prompts/loader.py`. Read each match to confirm none of them parse the *content* of the Pipeline Operators section (they should only load the file by path). If any code does parse it, surface that to the user before continuing.

- [ ] **Step 3: Run the full suite**

Run: `pytest -v`
Expected: full suite green. The handler chain reads `root.md` as opaque text and just bundles it, so trimming a section should not affect any test.

- [ ] **Step 4: Commit**

```bash
git add src/pal/prompts/bundled/root.md
git commit -m "docs(prompts): drop redundant Pipeline Operators section from root.md

The parse_pipeline tool description is now the canonical grammar reference."
```

---

## Task 9: Pre-merge verification

Final sweep: format, lint, type-check, and full pytest run. Required before declaring the feature done — never skip.

- [ ] **Step 1: Format**

Run: `black src tests`
Expected: either "All done!" or files reformatted. If files were changed, review the diff with `git diff` and commit them.

- [ ] **Step 2: Lint with autofix**

Run: `ruff check --fix src tests`
Expected: "All checks passed!" or trivial autofixes applied. Review and commit if changed.

- [ ] **Step 3: Type-check**

Run: `mypy src`
Expected: "Success: no issues found in N source files." If there are errors, fix them — `pipeline.py` uses standard library only and should type-check cleanly; the most likely failure is a missing import or a return-type mismatch in `parse_pipeline` (it must return `str`, not `list[dict]`).

- [ ] **Step 4: Full pytest run**

Run: `pytest -v`
Expected: full green. Net new test count: 29 in `tests/test_pipeline.py` (Tasks 1-5) plus 5 in `tests/test_registry.py` (Task 6 adds `parse_pipeline_schema` + `parse_pipeline_description_documents_grammar`; Task 7 adds 3 rejection tests) = 34 new tests. `test_all_tools_registered` in `test_registry.py` is modified, not added.

- [ ] **Step 5: Manual smoke against the running server (optional but recommended)**

If a dev environment is handy, start the server and exercise the new tool from an MCP client:

```bash
PAL_TRANSPORT=stdio pal
```

Then from the client, call `parse_pipeline("notes search docker | summarize")` and confirm the JSON response. Then call `run_pal_command("a | b")` and confirm the error directs to `parse_pipeline`. If you don't have an MCP client wired up, the unit tests in Tasks 6-7 already exercise both the schema and the rejection path, so this step is non-blocking.

- [ ] **Step 6: Final commit (only if Steps 1-3 produced changes)**

```bash
git add -A
git commit -m "chore: black/ruff cleanup for pipeline grammar work"
```

If Steps 1-3 produced no changes, skip this step.

---

## Spec coverage check (against the brief)

| Brief item | Where covered |
|---|---|
| `parse_pipeline` tool returning JSON stages | Task 6 |
| `run_pal_command` rejects pipeline strings | Task 7 |
| Left-to-right scan | Tasks 2-3 (`tokenize_pipeline` impl) |
| ` -- ` raw-mode edge marker stops tokenization | Task 3 |
| Operators recognised only space-surrounded | Tasks 2, 4 |
| Pass-through for `||`, `?foo&bar`, `:|`, emoji, unicode | Tasks 3, 4 |
| Variable substitution stays LLM-side | Task 4 (`$5` opaque test) — code does nothing with `$` |
| No quoting / no escape sequences | Confirmed by absence in `pipeline.py`; documented in module docstring & tool description (Tasks 1, 6) |
| Unit tests for every brief example | Tasks 1-4 (every test case from brief §Verification approach #1 is present) |
| Integration test: tool registered with expected schema | Task 6 |
| `root.md` pipeline section removed | Task 8 |
| Tokenizer description includes the `--` user-facing rule | Task 6 (docstring includes the "place free-form text after ` -- `" example) |

**Behavioural test (brief §Verification #3 — LLM calls parse_pipeline before pipeline-bearing run_pal_command):** mechanically enforced by the Task 7 rejection rather than by a fixture-driven LLM simulation. Tradeoff: simpler than maintaining a fixture conversation, but doesn't verify the *happy path* of an LLM correctly orchestrating multi-stage execution — that's exercised only in real use.

**Optional quoting (brief grammar rule #4):** explicitly out of scope per design decision. The ` -- ` edge marker is the universal escape; if quoting becomes necessary later it can be added without changing the operator-detection contract.
