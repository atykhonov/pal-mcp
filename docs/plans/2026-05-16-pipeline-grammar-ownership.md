# Brief: Establish a single source of truth for pipeline grammar

**Status:** proposed, not yet scheduled
**Author:** session analysis 2026-05-16
**Estimated effort:** ~3-5 hours (tokenizer + tool + tests)
**Related:** [2026-05-16-protocol-header-hoist.md](2026-05-16-protocol-header-hoist.md)

## Problem

Command grammar is **split across Python and the LLM** with no single source of
truth.

- `src/pal/tools/parser.py` only extracts the namespace (first token) — 53 lines,
  zero pipeline awareness.
- Pipeline operators (`|`, `&&`, `;`), the `--` raw-text delimiter, and
  variable substitution rules live in prose form in
  `src/pal/prompts/bundled/root.md` and rely entirely on the LLM following
  them.

This works for happy-path cases like `$$echo Hello | tr` but fails or
degrades silently when:

1. **Cold start**: built-in commands (`$$echo`, `$$prompt`, `$$help`) bypass
   `handle_standard_prompt` in `src/pal/tools/handlers.py:342-347` and never
   ship `root.md`. The most common pipeline starters never give the LLM
   the pipeline rules — the LLM has to remember them from prior training
   or a prior call.
2. **`--` delimiter ambiguity**: `$$prompt foo -- bar | baz` should not be
   a pipeline, but enforcement is "LLM, please remember the rule." Nothing
   in code prevents misinterpretation.
3. **Operator edge cases**: spacing rules (` | ` must be space-surrounded
   per `root.md`), quoting, and escaping have no mechanical specification.
4. **No test surface**: `tests/test_parser.py` can only assert
   `split(None, 1)` behavior. Pipeline semantics are untestable from Python.

## Constraint that shapes the solution

**Variable substitution must stay LLM-side.** Variables like `$MSG`, `$REPLY`,
`$REPLY1..N`, `$REPLIES`, and heading-based variables reference conversation
state that the MCP server does not have. The server cannot substitute these
because it cannot see the conversation. This means the LLM will always retain
some grammar responsibilities — the question is what to move *off* its plate.

## Proposed approach (recommended)

**Add a `parse_pipeline` tool that owns operator tokenization in Python.
Keep `run_pal_command` as a single-command executor.**

The flow becomes:

1. LLM sees user input with `$$` prefix.
2. LLM substitutes variables (`$MSG`, `$REPLY`, etc.) — unchanged.
3. LLM calls a new `parse_pipeline(command_string)` tool. The server returns
   a structured representation:
   ```json
   [
     {"cmd": "echo Hello", "op": "|"},
     {"cmd": "tr",         "op": null}
   ]
   ```
4. LLM iterates stages, calling `run_pal_command(stage.cmd)` per stage,
   passing previous output forward when `op == "|"`, applying short-circuit
   when `op == "&&"`, etc. The operator semantics are documented in the
   `parse_pipeline` tool description (which is shipped automatically).
5. `run_pal_command` itself **rejects** strings containing unescaped
   operators — enforcing that callers go through `parse_pipeline` first.

### Why this shape

- **Tokenization is mechanical** — quoting, ` -- ` delimiter handling,
  operator splitting, escape sequences all have one Python implementation
  with full unit-test coverage.
- **Execution stays LLM-orchestrated** — because prompt-based commands
  return instructions *for the LLM* (not data), the LLM must remain in the
  execution loop. A pure server-side pipeline executor cannot work for
  mixed built-in/prompt-based chains.
- **Grammar is discoverable** — the `parse_pipeline` tool's schema and
  description become the canonical reference. No more "is the spec in
  `root.md` or in the LLM's training?"
- **Composable with custom prompts** — custom prompts work unchanged
  because they only ever execute one stage at a time.

## Alternatives considered

### A. Move everything (including execution) into Python

Reject. Prompt-based commands fundamentally need an LLM to execute their
returned instructions. A server-side `run_pal_pipeline` would have to
either (a) refuse mixed pipelines, or (b) yield mid-pipeline to the LLM
for prompt-based stages — at which point you've reinvented the LLM-as-
orchestrator model with extra steps.

### B. Keep grammar in `root.md`, just ship it more reliably

The protocol-header-hoist brief covers this. It reduces the cold-start
problem but does not fix:
- Untestability of pipeline semantics.
- The `--` delimiter rule remaining LLM-enforced.
- Drift between prose spec and actual behavior.

Worth doing **in addition** but not sufficient.

### C. Make `run_pal_command` accept pipelines directly and return a
"continue execution" envelope

Workable but couples the executor and the parser. Forces every caller to
understand the envelope format. The `parse_pipeline` split keeps each tool
single-purpose.

## Trade-offs / open questions

1. **Two tools instead of one** adds surface area. Mitigated by the fact
   that `parse_pipeline` is small, focused, and only called for pipelines
   (single commands skip it).
2. **Escape model**: lean on the ` -- ` delimiter, not on quoting.
   Quoting-based escapes (POSIX-shell-style `\"`, `\\`, etc.) push
   escape pain onto the user/LLM and get ugly fast for long free-form
   text. The ` -- ` edge marker says "rest of input is opaque" — one
   concept, one position, no inner-content escape rules. See the
   "Tokenizer grammar" section below.
3. **What happens to `root.md`?** Its pipeline section becomes
   redundant once `parse_pipeline` exists. Strip it (also reduces
   per-call token cost — see the hoist brief).

## Tokenizer grammar (concrete rules)

The grammar is intentionally minimal. Two concepts: operators and a
raw-mode edge marker.

```
1. Scan left-to-right.
2. If the literal token ` -- ` (space-dash-dash-space) is encountered:
   stop tokenizing. Everything to the right is one final raw stage —
   no further operator recognition, no escape processing.
3. Otherwise, recognise operators only when space-surrounded:
   - ` | `  (space-pipe-space)     → operator: pipe
   - ` && ` (space-and-and-space)  → operator: and
   - ` ; `  (space-semi-space)     → operator: seq
4. Optional minimal quoting: `'...'` for single-token args containing
   spaces. NO escape sequences inside (no `\'`, `\n`, `\\`). If you
   need a literal apostrophe inside the quoted region, restructure
   the command to end with ` -- ` and put the payload there.
5. All other characters — Unicode, emoji, newlines, parentheses,
   `$`, `?`, `&`, `|` without surrounding spaces, etc. — are opaque
   bytes and pass through untouched.
```

### Design rationale

- **Space-surrounded operators** mean accidental punctuation never
  triggers pipeline parsing. `$$echo a|b` is one stage; `$$echo a | b`
  is two. URLs (`?foo&bar`), code snippets, emoticons (`:|`), and
  filenames with operator-shaped characters all pass through harmlessly.
  This also means `||` is never tokenized as an operator (no ` | `
  substring exists inside ` || `) — it passes through as opaque
  punctuation. Users wanting "or-else" semantics get one stage, not
  a confusing partial parse.
- **` -- ` as the universal escape** matches POSIX argument conventions
  (`rm -- -weird-filename`, `git checkout -- file`). Edge markers beat
  region markers: once you've signalled raw mode, internal quotes,
  pipes, ampersands, and backslashes are all just bytes. No nested
  escape rules.
- **No backslash escapes, no double-quote regions** because they re-
  introduce the very escape-hell that pushed us away from quoting in
  the first place. The cost of supporting them is paid on every input;
  the value is realised only in obscure mid-command cases the LLM can
  always restructure around.

### LLM-facing rule (to embed in `parse_pipeline` tool description)

> "When constructing a `$$command` with free-form text (translations,
> summaries, search queries, anything containing user-provided
> content), place the content at the end and prefix it with ` -- `.
> This activates raw mode and prevents accidental operator parsing.
> Example: `$$tr -- $MSG` not `$$tr $MSG`."

## Verification approach

1. **New unit tests** in `tests/test_pipeline_parser.py`:
   - `parse("echo hello")` → 1 stage.
   - `parse("echo hello | tr")` → 2 stages, op=`|`.
   - `parse("foo && bar")` → 2 stages, op=`&&`.
   - `parse("foo ; bar")` → 2 stages, op=`;`.
   - `parse("tr -- hello | world")` → 1 stage, cmd=`tr -- hello | world`.
   - `parse("tr -- 你好 | мир 🌍")` → 1 stage, cmd=`tr -- 你好 | мир 🌍`.
   - `parse("echo a|b")` → 1 stage (no spaces around `|`).
   - `parse("echo --help")` → 1 stage (no spaces around `--`).
   - `parse("a || b")` → 1 stage (no ` | ` substring; `||` is opaque
     punctuation, not a recognized operator).
   - `parse("cmd -- foo -- bar | baz")` → 1 stage,
     cmd=`cmd -- foo -- bar | baz` (second `--` is part of payload).
   - `parse("notes search docker | summarize")` → 2 stages.
   - `parse("echo $5 && cat")` → 2 stages (`$` is opaque to the
     tokenizer; variable substitution remains LLM-side, upstream).
   - Optional quoting (if implemented): `parse("echo 'hello world'")`
     → 1 stage with arg `hello world`; quotes stripped.
2. **Integration test** in `tests/test_registry.py`:
   - `parse_pipeline` tool is registered with the expected schema.
3. **Behavioural test**: simulate the LLM flow against a fixture
   conversation asserting that `parse_pipeline` is called before any
   pipeline-containing `run_pal_command`.

### Known corner case to document for users

The literal sequence ` -- ` always means "start raw mode." A user who
types `$$echo Test -- followed by content` will get one stage with the
entire payload after `--` treated as raw — which is usually what they
want anyway, since no operators are present. Worth one sentence in
user-facing docs so this isn't a surprise.

## Expected outcome

- Pipeline grammar has one definition (`parse_pipeline` implementation +
  its tool description).
- `tests/test_pipeline_parser.py` can mechanically verify edge cases that
  today only the LLM enforces.
- Cold-start failures for pipelines starting with built-ins disappear —
  the LLM gets pipeline rules via the `parse_pipeline` tool schema, which
  is loaded on demand.
- `root.md` shrinks (synergy with protocol-header-hoist brief).

## Out of scope

- Variable substitution moves (cannot move — needs conversation state).
- Server-side pipeline execution (rejected; see Alternative A).
- New operators beyond `|`, `&&`, `;` already documented in `root.md`.
- Streaming intermediate pipeline outputs (could be a follow-up).
