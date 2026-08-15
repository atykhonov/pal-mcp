# Protocol Header Hoist Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop re-broadcasting the static PAL protocol header on every prompt-based `$$command` response by hoisting it into the MCP server's `instructions` field, saving ~500 tokens per call.

**Architecture:** Extract the protocol Markdown from `src/pal/prompts/bundled/root.md` into a new `src/pal/protocol.py` constant. Add a `PAL_PROTOCOL_HEADER_LOCATION` env var with three values — `instructions` (default, ships once via FastMCP's `instructions=` field), `per-call` (prepends to every prompt response, omits from `instructions=`), and `both` (includes in both places). Default `instructions` reclaims ~500 tokens per prompt-based call; `per-call` covers harnesses that ignore server `instructions`; `both` covers harnesses that re-broadcast `instructions` AND want it inline anyway.

**Important caveat — discovery vs. interpretation:** The `instructions` field carries two distinct payloads: the **call-out sentence** ("when you see `$$`, call `run_pal_command`" — the *discovery/trigger* signal that routes input to the tool) and the **protocol body** (what `$$echo`, `$MSG`, etc. mean — the *interpretation* signal for bundled prompts a tool call returns). `per-call` mode only restores the interpretation half — the discovery half cannot ride on tool responses because tool-response content reaches the LLM only *after* a call has already been made. On harnesses that fully ignore `instructions`, operators must also add the call-out to their user-side system prompt (CLAUDE.md, Cursor system prompt, etc.) for discovery to work. See trade-off #2 in `2026-05-16-protocol-header-hoist.md` for the full deployment matrix.

**Tech Stack:** Python 3, FastMCP, pydantic-settings, pytest, pytest-asyncio.

---

## Source brief

This plan implements `docs/plans/2026-05-16-protocol-header-hoist.md`. Re-read that file before starting if needed.

## File Structure

**New file:**
- `src/pal/protocol.py` — exports `PROTOCOL_INSTRUCTIONS` (module-level `str` constant). Single responsibility: hold the protocol Markdown that MCP clients receive at session init. No imports from PAL internals.

**Modified files:**
- `src/pal/tools/registry.py` — adds a `_build_server_instructions(location)` helper; `SERVER_INSTRUCTIONS` is built from that helper using `get_settings().protocol_header_location`. Includes `PROTOCOL_INSTRUCTIONS` when location is `instructions` or `both`; otherwise just the call-out sentence.
- `src/pal/tools/handlers.py` — `handle_standard_prompt` reads `get_settings().protocol_header_location`; when value is `per-call` or `both`, prepends `PROTOCOL_INSTRUCTIONS`; when value is `instructions` (default), skips the prepend.
- `src/pal/config.py` — adds `protocol_header_location: Literal["instructions", "per-call", "both"] = "instructions"` field with `PAL_PROTOCOL_HEADER_LOCATION` env var.
- `src/pal/prompts/loader.py` — removes `"root"` from `_INTERNAL_PROMPTS` (line 496) since the file is being deleted; the filter set no longer needs the entry.

**Deleted files:**
- `src/pal/prompts/bundled/root.md` — content moves to `protocol.py`.

**Test files:**
- `tests/test_protocol.py` (new) — verifies the `PROTOCOL_INSTRUCTIONS` constant has the expected sections.
- `tests/test_registry.py` — extends `test_server_instructions` to assert protocol content is present in `mcp.instructions`.
- `tests/test_handlers.py` — updates `TestHandleStandardPrompt`: existing tests change to assert the protocol header is **absent** by default (`instructions` mode); one new test asserts the header **is present** when `protocol_header_location` is set to `per-call` (and equivalently `both`).

---

## Task 1: Extract protocol content into a Python module

**Files:**
- Create: `src/pal/protocol.py`
- Test: `tests/test_protocol.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_protocol.py`:

```python
"""Tests for the hoisted PAL protocol instructions constant."""

from __future__ import annotations

from pal.protocol import PROTOCOL_INSTRUCTIONS


def test_protocol_contains_builtin_command_names() -> None:
    """The protocol header must name every built-in command the LLM can invoke."""
    for name in ("$$echo", "$$prompt", "$$help"):
        assert name in PROTOCOL_INSTRUCTIONS, f"missing {name!r}"


def test_protocol_contains_variable_substitution_section() -> None:
    """The protocol header must document the $MSG / $REPLY variables."""
    assert "$MSG" in PROTOCOL_INSTRUCTIONS
    assert "$REPLY" in PROTOCOL_INSTRUCTIONS


def test_protocol_contains_executing_prompt_section() -> None:
    """The protocol header must explain how to interpret bundled prompts."""
    assert "Executing Prompt-Based Commands" in PROTOCOL_INSTRUCTIONS


def test_protocol_contains_error_handling_section() -> None:
    """The protocol header must keep the error-reporting guidance."""
    assert "Error Handling" in PROTOCOL_INSTRUCTIONS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_protocol.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pal.protocol'`.

- [ ] **Step 3: Create the protocol module**

Create `src/pal/protocol.py`:

```python
"""PAL protocol instructions sent to MCP clients at session init.

This module exports `PROTOCOL_INSTRUCTIONS`: the static Markdown describing
the PAL command protocol. FastMCP ships it once via the `instructions` field
during the `initialize` handshake, so prompt-based command responses no
longer need to re-broadcast it on every call.

Previously this content lived in `src/pal/prompts/bundled/root.md` and was
prepended to every `handle_standard_prompt` response (~500 tokens/call).
"""

from __future__ import annotations

PROTOCOL_INSTRUCTIONS = """# PAL Command Protocol

## Built-in Commands

These commands execute directly and return results:
- `$$echo <text>` - Echo text with variable substitution
- `$$prompt [name] [-- content]` - List/view/create custom prompts (use `--` to separate name from content)
- `$$help` - Show all available commands

## Variable Substitution

Available variables:
- `$MSG` - User's previous message
- `$REPLY` - Your previous response
- `$REPLY1`, `$REPLY2`, ... - Older responses (1 back, 2 back, etc.)
- `$REPLIES` - All your previous responses (concatenated)
- Heading variables: `## Summary` creates `$SUMMARY`

## Executing Prompt-Based Commands

When you receive bundled prompts (this response):
1. Read the Command and Subcommand sections below
2. Parse the User Input section for arguments and content
3. Execute using the pal_curl tool as described in the prompts
4. Format output as specified in the prompts

## Error Handling

Report errors clearly with usage hints. Example:
```
Error: Missing required content
Usage: $$notes add [-t tags] <content>
```
"""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_protocol.py -v`
Expected: PASS — all 4 tests green.

- [ ] **Step 5: Commit**

```bash
git add src/pal/protocol.py tests/test_protocol.py
git commit -m "feat(protocol): add PROTOCOL_INSTRUCTIONS constant for MCP instructions field"
```

---

## Task 2: Wire PROTOCOL_INSTRUCTIONS into FastMCP `instructions=`

**Files:**
- Modify: `src/pal/tools/registry.py:22-25`
- Test: `tests/test_registry.py:62-64`

**Note:** Task 3 (adding the `protocol_header_location` setting) is a prerequisite for the helper introduced here. If you prefer strict TDD-first ordering, do Task 3 before Task 2. The plan keeps Task 2 first to preserve the brief's "wire instructions, then add toggle" narrative; either order works as long as both land before Task 4.

- [ ] **Step 1: Strengthen the failing test**

Replace the existing `test_server_instructions` in `tests/test_registry.py` (current lines 62-64) with two tests — one verifying the default live `mcp.instructions`, one exercising the helper across all three locations:

```python
    def test_server_instructions_default_includes_protocol(self) -> None:
        """Default config ('instructions') puts the protocol into mcp.instructions."""
        instructions = mcp.instructions or ""
        # Call-out sentence directing the LLM to run_pal_command
        assert "$$" in instructions
        assert "run_pal_command" in instructions
        # Hoisted protocol content (built-in command names + variables)
        assert "$$echo" in instructions
        assert "$$prompt" in instructions
        assert "$$help" in instructions
        assert "$MSG" in instructions
        assert "Executing Prompt-Based Commands" in instructions

    def test_build_server_instructions_per_call_omits_protocol(self) -> None:
        """'per-call' mode strips the protocol from the instructions string."""
        from pal.tools.registry import _build_server_instructions

        built = _build_server_instructions("per-call")
        assert "run_pal_command" in built  # call-out kept
        assert "$$echo" not in built       # protocol stripped
        assert "Executing Prompt-Based Commands" not in built

    def test_build_server_instructions_both_includes_protocol(self) -> None:
        """'both' mode keeps the protocol in the instructions string."""
        from pal.tools.registry import _build_server_instructions

        built = _build_server_instructions("both")
        assert "run_pal_command" in built
        assert "$$echo" in built
        assert "Executing Prompt-Based Commands" in built
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_registry.py -v`
Expected: FAIL — the helper doesn't exist yet, and `mcp.instructions` is still the one-sentence call-out.

- [ ] **Step 3: Add the helper and rebuild `SERVER_INSTRUCTIONS`**

In `src/pal/tools/registry.py`, add the `Literal` import to the existing typing-related imports (near the top), add the `pal.config.get_settings` import if not already present, and add the `pal.protocol` import alphabetically between `pal.prompts` and `pal.tools.curl` (NOT after `pal.tools.pipeline` — that would break alphabetical ordering).

Then replace lines 22-25:

```python
SERVER_INSTRUCTIONS = (
    "When you see $$ at the start of user input, "
    "call run_pal_command with the command text."
)
```

with:

```python
from typing import Literal

_CALL_OUT = (
    "When you see $$ at the start of user input, "
    "call run_pal_command with the command text."
)


def _build_server_instructions(
    location: Literal["instructions", "per-call", "both"],
) -> str:
    """Compose the MCP `instructions` payload based on protocol-header location.

    'instructions' / 'both' — embed the full protocol so MCP clients receive
    it once during `initialize`. 'per-call' — keep only the call-out sentence
    so the protocol arrives only via per-call prepend (see handlers.py).
    """
    if location in ("instructions", "both"):
        return f"{_CALL_OUT}\n\n{PROTOCOL_INSTRUCTIONS}"
    return _CALL_OUT


SERVER_INSTRUCTIONS = _build_server_instructions(
    get_settings().protocol_header_location
)
```

The `get_settings()` call here runs once at module import — the `Literal` value is fixed for the process lifetime, which matches operator expectations (env vars don't change mid-process).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_registry.py -v`
Expected: PASS — all registry tests green, including the three new `test_server_instructions_*` / `test_build_server_instructions_*` tests.

- [ ] **Step 5: Commit**

```bash
git add src/pal/tools/registry.py tests/test_registry.py
git commit -m "feat(registry): compose FastMCP instructions from PAL_PROTOCOL_HEADER_LOCATION"
```

---

## Task 3: Add `protocol_header_location` setting

**Files:**
- Modify: `src/pal/config.py` (add field next to other PAL_* settings)
- Add a small unit test alongside the rest of the test suite (any existing settings test module, or a new `tests/test_config.py` if none exists).

- [ ] **Step 1: Write the failing tests**

In `tests/test_config.py` (create if missing), add:

```python
"""Tests for PAL settings."""

from __future__ import annotations

import pytest

from pal.config import Settings


def test_protocol_header_location_default_is_instructions() -> None:
    """Default location ships the protocol via FastMCP `instructions`."""
    assert Settings().protocol_header_location == "instructions"


@pytest.mark.parametrize("value", ["instructions", "per-call", "both"])
def test_protocol_header_location_accepts_all_modes(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    """All three documented values round-trip via the env var."""
    monkeypatch.setenv("PAL_PROTOCOL_HEADER_LOCATION", value)
    assert Settings().protocol_header_location == value


def test_protocol_header_location_rejects_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pydantic validates the Literal — typos fail at startup, not silently."""
    monkeypatch.setenv("PAL_PROTOCOL_HEADER_LOCATION", "per_call")  # typo (underscore)
    with pytest.raises(Exception):  # pydantic.ValidationError
        Settings()
```

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `protocol_header_location` doesn't exist on `Settings` yet.

- [ ] **Step 2: Add the setting**

In `src/pal/config.py`, add this field inside the `Settings` class, immediately after the `log_level` field (around line 47):

```python
    protocol_header_location: Annotated[
        Literal["instructions", "per-call", "both"],
        Field(
            description=(
                "Where to surface the PAL protocol header to the LLM. "
                "'instructions' (default): include in FastMCP `instructions` "
                "field only — shipped once per session, saves ~500 tokens per "
                "prompt-based call. 'per-call': prepend to every prompt response "
                "and omit from `instructions` — use when your MCP harness ignores "
                "or doesn't surface server instructions. 'both': include in "
                "`instructions` AND prepend per-call — use only when your harness "
                "re-broadcasts `instructions` and you want belt-and-suspenders. "
                "NOTE on 'per-call': this only restores the *interpretation* of "
                "bundled prompts ($MSG, $$echo, etc.). It does NOT restore the "
                "*discovery* signal (the call-out telling the LLM to invoke "
                "run_pal_command on $$-prefixed input), because tool responses "
                "only reach the LLM after a tool call. If your harness ignores "
                "`instructions`, also add 'when input starts with $$, call "
                "run_pal_command' to your user-side system prompt (CLAUDE.md, "
                "Cursor system prompt, etc.)."
            ),
        ),
    ] = "instructions"
```

`Literal` is already imported from `typing` at the top of `config.py` (used by `transport` and `notes_ai_provider`), so no new import is needed.

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: PASS — all three tests green.

- [ ] **Step 4: Sanity-check the env wiring end-to-end**

```bash
python -c "from pal.config import Settings; print(Settings().protocol_header_location)"
# Expected: instructions

PAL_PROTOCOL_HEADER_LOCATION=per-call python -c "from pal.config import Settings; print(Settings().protocol_header_location)"
# Expected: per-call

PAL_PROTOCOL_HEADER_LOCATION=both python -c "from pal.config import Settings; print(Settings().protocol_header_location)"
# Expected: both
```

Note: each invocation uses a fresh `Settings()` so the `@lru_cache` on `get_settings()` doesn't interfere.

- [ ] **Step 5: Commit**

```bash
git add src/pal/config.py tests/test_config.py
git commit -m "feat(config): add PAL_PROTOCOL_HEADER_LOCATION setting (instructions|per-call|both)"
```

---

## Task 4: Drop the root.md prepend from `handle_standard_prompt`

**Files:**
- Modify: `src/pal/tools/handlers.py:283-336`
- Modify: `tests/test_handlers.py:200-307`

- [ ] **Step 1: Rewrite the affected tests for the new default behavior**

In `tests/test_handlers.py`, replace `TestHandleStandardPrompt` (current lines 201-307) with:

```python
class TestHandleStandardPrompt:
    """Tests for handle_standard_prompt handler.

    Default (PAL_PROTOCOL_HEADER_LOCATION=instructions): the handler
    returns just the bundled command body + user input — the protocol
    header is shipped to the client once via the MCP `instructions`
    field, not per-call.

    Setting PAL_PROTOCOL_HEADER_LOCATION to 'per-call' or 'both'
    prepends the header to every response (covers harnesses that ignore
    server instructions, or operators who want belt-and-suspenders).
    """

    def test_omits_protocol_header_by_default(self) -> None:
        """No `# PAL Protocol` block in the response when location is 'instructions'."""

        def mock_load_merged(path_parts: list[str]) -> str | None:
            key = tuple(path_parts)
            return {("test",): "Test content"}.get(key)

        with patch(
            "pal.tools.handlers.load_merged_prompt", side_effect=mock_load_merged
        ):
            cmd = ParsedCommand(namespace="test", rest="")
            result = handle_standard_prompt(cmd)
            assert "# PAL Protocol" not in result.output
            assert "# Command: test" in result.output
            assert "Test content" in result.output

    @pytest.mark.parametrize("location", ["per-call", "both"])
    def test_includes_protocol_header_when_location_requests_per_call(
        self, location: str
    ) -> None:
        """'per-call' and 'both' both prepend the protocol header."""

        def mock_load_merged(path_parts: list[str]) -> str | None:
            key = tuple(path_parts)
            return {("test",): "Test content"}.get(key)

        with (
            patch(
                "pal.tools.handlers.load_merged_prompt", side_effect=mock_load_merged
            ),
            patch(
                "pal.tools.handlers.get_settings"
            ) as mock_get_settings,
        ):
            mock_get_settings.return_value.protocol_header_location = location
            cmd = ParsedCommand(namespace="test", rest="")
            result = handle_standard_prompt(cmd)
            assert "# PAL Protocol" in result.output
            assert "# Command: test" in result.output

    def test_includes_rest_in_header(self) -> None:
        """handle_standard_prompt includes rest in header."""

        def mock_load_merged(path_parts: list[str]) -> str | None:
            key = tuple(path_parts)
            return {("test",): "Content"}.get(key)

        with patch(
            "pal.tools.handlers.load_merged_prompt", side_effect=mock_load_merged
        ):
            cmd = ParsedCommand(namespace="test", rest="-v")
            result = handle_standard_prompt(cmd)
            assert "## $$test -v" in result.output

    def test_includes_user_input(self) -> None:
        """handle_standard_prompt includes user input section."""

        def mock_load_merged(path_parts: list[str]) -> str | None:
            key = tuple(path_parts)
            return {("notes",): "Notes command"}.get(key)

        with patch(
            "pal.tools.handlers.load_merged_prompt", side_effect=mock_load_merged
        ):
            cmd = ParsedCommand(namespace="notes", rest="add hello world")
            result = handle_standard_prompt(cmd)
            # Since "add" doesn't have a file, it becomes part of user input
            assert "# User Input" in result.output

    def test_namespace_dir_without_root_file(self) -> None:
        """handle_standard_prompt works for namespace dirs without a root .md file.

        E.g., custom/wfi/start.md exists but custom/wfi.md does not.
        Running $$wfi start should find and load wfi/start.md.
        """

        def mock_load_merged(path_parts: list[str]) -> str | None:
            key = tuple(path_parts)
            return {
                # No ("wfi",) entry — simulates missing wfi.md
                ("wfi", "start"): "WFI start content",
            }.get(key)

        with patch(
            "pal.tools.handlers.load_merged_prompt", side_effect=mock_load_merged
        ):
            cmd = ParsedCommand(namespace="wfi", rest="start TRM-594")
            result = handle_standard_prompt(cmd)
            assert "# Command: wfi/start" in result.output
            assert "WFI start content" in result.output
            assert "# User Input" in result.output
            assert "TRM-594" in result.output
            # Should NOT show error
            assert "isn't defined" not in result.output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_handlers.py::TestHandleStandardPrompt -v`
Expected: FAIL — `test_omits_protocol_header_by_default` fails because the current handler unconditionally prepends `# PAL Protocol`; `test_includes_protocol_header_when_flag_enabled` may pass coincidentally (since the current code always includes the header), but the others still pass.

- [ ] **Step 3: Update `handle_standard_prompt` to gate the prepend on the location enum**

In `src/pal/tools/handlers.py`:

(a) Ensure `import pytest` is at the top of `tests/test_handlers.py` (the `@pytest.mark.parametrize` decorator added in Step 1 needs it).

(b) Add two imports near the top of `src/pal/tools/handlers.py`, alongside the existing `pal.*` imports — place `pal.config` between `pal.prompts` and `pal.tools.parser`, and `pal.protocol` between `pal.config` and `pal.tools.parser` (so the block stays alphabetical):

```python
from pal.config import get_settings
from pal.protocol import PROTOCOL_INSTRUCTIONS
```

(c) Replace the body of `handle_standard_prompt` (current lines 283-336) with:

```python
def handle_standard_prompt(
    command: ParsedCommand,
    ctx: RequestContext[ServerSession, object, object] | None = None,
) -> CommandResult:
    """Handle prompt-based commands - returns bundled prompts.

    Bundles command prompts + user input for the LLM to interpret. The
    PAL protocol header is shipped via the MCP `instructions` field by
    default. Set PAL_PROTOCOL_HEADER_LOCATION to 'per-call' (or 'both')
    to also prepend it to every response — for MCP harnesses that don't
    surface server instructions to the model.
    """
    parts: list[str] = []

    # 1. Optional per-call protocol header (off in default 'instructions' mode)
    if get_settings().protocol_header_location in ("per-call", "both"):
        parts.append(f"# PAL Protocol\n\n{PROTOCOL_INSTRUCTIONS}")

    # 2. Build token list from parsed command
    tokens = [command.namespace]
    if command.rest:
        tokens.extend(command.rest.split())

    # 3. Load prompt chain
    prompts, user_input = load_prompt_chain(tokens)

    # 4. Check if command exists
    if not prompts:
        # No command found - return helpful error message
        error_msg = (
            f"## $${command.namespace}\n\n"
            f"**Error:** The `$${command.namespace}` command isn't defined.\n\n"
            f"To create it:\n"
            f"```\n"
            f"$$prompt {command.namespace} Your instruction here\n"
            f"```"
        )
        return CommandResult(output=error_msg)

    # 5. Add each prompt in the chain
    for i, (path, content) in enumerate(prompts):
        if i == 0:
            parts.append(f"# Command: {path}\n\n{content}")
        else:
            parts.append(f"# Subcommand: {path}\n\n{content}")

    # 6. Include user input if any
    if user_input:
        parts.append(f"# User Input\n\n{user_input}")

    # 7. Build header for display
    header = f"## $${command.namespace}"
    if command.rest:
        header += f" {command.rest}"

    bundled = "\n\n---\n\n".join(parts)
    return CommandResult(output=f"{header}\n\n{bundled}")
```

Notes:
- `PROTOCOL_INSTRUCTIONS` is imported at the top of the file — Python caches it in `sys.modules` after Task 2 (where `registry.py` already imports it), so a top-level import here is essentially free and cleaner than a deferred-import idiom.
- `load_prompt` is no longer called from this function. Task 4 Step 4 below removes it from the import block.

- [ ] **Step 4: Drop the now-unused `load_prompt` import**

`handle_standard_prompt` was the only caller. Confirm with:

```bash
grep -n "load_prompt\b" /home/andrii/projects/pal/src/pal/tools/handlers.py
```

Expected: only the `from pal.prompts import (...)` line — no call sites. If anything else shows up, investigate before removing.

Then edit the import block at the top of `handlers.py` to drop `load_prompt`:

```python
from pal.prompts import (
    get_prompt_path,
    list_builtin_prompts,
    list_custom_prompts,
    list_subcommands,
    load_custom_prompt,
    load_merged_prompt,
    parse_frontmatter,
    save_custom_prompt,
)
```

- [ ] **Step 5: Run all handler tests**

Run: `pytest tests/test_handlers.py -v`
Expected: PASS — all of `TestHandleStandardPrompt` green, plus the rest of `test_handlers.py` unchanged.

- [ ] **Step 6: Run the full suite**

Run: `pytest`
Expected: PASS — full suite green. If any test fails because it implicitly relied on `# PAL Protocol` appearing in handler output, update it to match the new default.

- [ ] **Step 7: Commit**

```bash
git add src/pal/tools/handlers.py tests/test_handlers.py
git commit -m "feat(handlers): gate protocol header prepend on PAL_PROTOCOL_HEADER_LOCATION"
```

---

## Task 5: Delete `root.md` and clean up `_INTERNAL_PROMPTS`

**Files:**
- Delete: `src/pal/prompts/bundled/root.md`
- Modify: `src/pal/prompts/loader.py:496`

- [ ] **Step 1: Confirm no remaining references to root.md**

Run from the project root:

```bash
grep -rn "load_prompt(\"root\"\|'root'\|/root\.md" src tests
```

Expected output: Only `_INTERNAL_PROMPTS = {"root", "help", "curl"}` in `src/pal/prompts/loader.py:496`. (Anything else means a caller still expects `root.md` to exist — investigate before deleting.)

- [ ] **Step 2: Delete `root.md`**

```bash
git rm src/pal/prompts/bundled/root.md
```

- [ ] **Step 3: Remove `"root"` from `_INTERNAL_PROMPTS`**

In `src/pal/prompts/loader.py:496`, change:

```python
_INTERNAL_PROMPTS = {"root", "help", "curl"}
```

to:

```python
_INTERNAL_PROMPTS = {"help", "curl"}
```

- [ ] **Step 4: Run the full suite**

Run: `pytest`
Expected: PASS — no test should depend on `root.md` being a discoverable resource.

- [ ] **Step 5: Run lint and type checks**

Run these in parallel:

```bash
ruff check src tests
mypy src
```

Expected: Both clean. If `ruff` flags `load_prompt` as unused in `handlers.py` and you skipped Task 4 Step 4, fix it now.

- [ ] **Step 6: Commit**

```bash
git add src/pal/prompts/bundled/root.md src/pal/prompts/loader.py
git commit -m "refactor(prompts): delete root.md (content moved to pal.protocol)"
```

---

## Task 6: Manual smoke test

**Files:** None modified — verification only.

- [ ] **Step 1: Start the dev server**

In one terminal:

```bash
PAL_TRANSPORT=stdio pal
```

(Or use `pal` directly to start the SSE server on port 8090, whichever is easier to inspect.)

- [ ] **Step 2: Default mode (`instructions`) — send a prompt-based command and inspect**

Pick any prompt-based command that exists in your bundled set (any namespace under `src/pal/prompts/bundled/`). From an MCP client (Claude Code, Inspector, or a script), call:

```
run_pal_command(command="<some prompt-based command>")
```

Verify:
- Response body does NOT begin with `# PAL Protocol`
- Response body contains `# Command: <name>` and the command's prompt content
- The MCP `initialize` response (visible in `serverInfo.instructions` or your inspector's session view) DOES contain the full protocol — `$$echo`, `$$prompt`, `$$help`, `$MSG`, `Executing Prompt-Based Commands`, `Error Handling`.
- If you can measure: capture response token count and compare to a pre-change baseline — expected reduction ~500 tokens.

- [ ] **Step 3: `per-call` mode — verify per-call prepend, instructions stripped, discovery channel still intact**

Restart with:

```bash
PAL_PROTOCOL_HEADER_LOCATION=per-call pal
```

Re-run the same `run_pal_command(...)` call and verify:
- Response body DOES begin with `# PAL Protocol`
- The MCP `instructions` field contains ONLY the `$$` call-out sentence — no `$$echo`, `$MSG`, etc.
- Same command body present after the protocol header

Additionally verify the **discovery channel** still works on harnesses that ignore `instructions` entirely: list the tools via `tools/list` (in the Inspector, or via your client's tool-discovery view) and confirm the `run_pal_command` description still mentions `$$`. The tool description is PAL's fallback discovery path — if it ever stops mentioning `$$`, the LLM has no way to route `$$notes list` to PAL without an explicit user-side system prompt entry.

```bash
# Quick sanity check from the project root:
grep -n '\$\$' src/pal/tools/registry.py
```

Expected: at minimum the `run_pal_command` docstring contains `$$` (currently `"""Execute a single PAL $$ command stage."""`). If a future refactor removes it, the discovery story breaks for harnesses that ignore `instructions`.

This is the mode for harnesses that ignore `instructions` OR re-broadcast it on every turn (you avoid double-paying for the protocol bytes). Pair it with a user-side system prompt entry if your harness ignores `instructions` entirely — see brief trade-off #2.

- [ ] **Step 4: `both` mode — verify protocol in both places**

Restart with:

```bash
PAL_PROTOCOL_HEADER_LOCATION=both pal
```

Verify:
- Response body DOES begin with `# PAL Protocol`
- MCP `instructions` field ALSO contains the full protocol

This is the belt-and-suspenders mode for unknown/flaky harnesses — uses the most tokens, recommended only as a temporary diagnostic.

- [ ] **Step 5: Commit any incidental fixes (only if needed)**

If smoke testing surfaced anything, fix and commit. Otherwise skip — this task has no required commit.

---

## Verification summary

After all tasks:
- `pytest` — full suite green.
- `ruff check src tests` — clean.
- `mypy src` — clean.
- `black --check src tests` — clean (or run `black src tests` if reformat needed).
- Smoke test confirms response body is ~500 tokens shorter for prompt-based commands by default (`instructions` mode), `per-call` mode prepends the header AND strips it from `mcp.instructions`, and `both` mode includes it in both places.

## Out of scope

Same as the brief — trimming `root.md` further, harness-level dedup, caching `list_pal_commands`. Don't widen scope.

Also out of scope: writing user-facing setup docs that explain when to add the call-out to a user-side system prompt (CLAUDE.md, etc.). The config field's `description=` text and brief trade-off #2 are sufficient for now; a dedicated user-facing deployment guide is a follow-up if/when real users report discovery failures on harnesses that ignore `instructions`.
