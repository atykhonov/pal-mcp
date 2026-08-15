# Brief: Hoist `root.md` protocol header out of per-call responses

**Status:** proposed, not yet scheduled
**Author:** session analysis 2026-05-16
**Estimated effort:** ~1 hour implementation + tests

## Problem

Every prompt-based `$$command` response currently re-broadcasts the full
"PAL Protocol" section (built-in command list, variable substitution rules,
pipeline operators, error handling) from `src/pal/prompts/bundled/root.md`.

This block is **static across a session** and **identical across all calls**,
but it adds roughly 500 tokens to every prompt-based command response. A
session that runs 10 prompt-based commands burns ~5K tokens re-stating
information the LLM already has in conversation history.

Built-in commands (`$$echo`, `$$prompt`, `$$help`) are unaffected — they
bypass the standard prompt handler and don't pay this cost.

## Where the waste lives

- `src/pal/tools/handlers.py:283-336` — `handle_standard_prompt` unconditionally
  prepends `root.md` to every response (lines 294-296).
- `src/pal/prompts/bundled/root.md` — the source of the protocol header.
- `src/pal/tools/registry.py:21-24` — `SERVER_INSTRUCTIONS` is currently a
  single sentence; the natural home for hoisted static content.

## Proposed fix

Move the static portions of `root.md` into the FastMCP `instructions`
field on the `mcp = FastMCP(...)` construction in `registry.py:26-30`.
The MCP harness ships server instructions to the client once per session,
so the protocol info would be present in context without per-call repetition.

Then in `handle_standard_prompt`, gate the `root.md` prepend on a
`PAL_PROTOCOL_HEADER_LOCATION` env var (`instructions` | `per-call` |
`both`, default `instructions`) so operators can choose where the
protocol surfaces. See trade-off #2 below for why a single boolean
isn't enough — and why even the per-call fallback only solves half the
problem on harnesses that drop `instructions`.

## What to keep in per-call responses

The bundled command body itself, any subcommand bodies in the chain, and
user input — i.e. everything `handle_standard_prompt` already builds in
steps 2-6. Only step 1 (the root.md prepend) is the target.

## Trade-offs / open questions

1. **Clients that ignore server `instructions`** — some MCP harnesses
   don't surface the `instructions` field to the model (older SDKs,
   multi-server budget policies, trust-boundary defenses against prompt
   injection, or UI-only treatment). Mitigation: a `PAL_PROTOCOL_HEADER_LOCATION`
   env var with three values:
   - `instructions` (default) — protocol shipped once via `instructions=`
   - `per-call` — protocol prepended to every tool response; stripped
     from `instructions=` so harnesses that re-broadcast it on every
     turn don't double-pay
   - `both` — protocol in both places, diagnostic/belt-and-suspenders

   See the **Discovery vs. interpretation** section below — the flag is
   not a complete substitute for a working `instructions` channel.

2. **Discovery vs. interpretation (important, easy to miss)** — the
   `instructions` field does two distinct jobs:

   - **Discovery / trigger** — the call-out sentence ("when you see
     `$$`, call `run_pal_command`") tells the LLM to route `$$`-prefixed
     input to the tool *in the first place*.
   - **Interpretation** — the protocol body explains what `$$echo`,
     `$MSG`, `Executing Prompt-Based Commands`, etc. mean, so the LLM
     knows what to do with the bundled prompts a tool call returns.

   `per-call` mode only restores the **interpretation** half: the
   protocol body rides along with every tool response. It *cannot*
   restore the **discovery** half, because tool-response content reaches
   the LLM only *after* a tool call has already been made.

   If a harness fully ignores `instructions`, the LLM has three other
   discovery channels:
   - **Tool descriptions** (always surfaced via `tools/list`) — the
     `run_pal_command` docstring already mentions `$$`, so capable models
     often pattern-match correctly. Reliable but not deterministic.
   - **User-side system prompt** — adding "when input starts with `$$`,
     call `run_pal_command`" to `CLAUDE.md`, Cursor's system prompt,
     etc. This is the **most reliable** mitigation.
   - **Model inference** — Claude 4.x and similar often recognize the
     `$$` convention from context alone. Stochastic.

   **Operator guidance:** on harnesses that ignore `instructions`, set
   `PAL_PROTOCOL_HEADER_LOCATION=per-call` AND add the call-out sentence
   to your user-side system prompt. One without the other leaves a gap.

3. **`root.md` isn't 100% static today** — check whether anything in it
   references runtime state (variable values, dynamic command list, etc.).
   If yes, split: static parts → instructions, dynamic parts → per-call.
   On quick read, `root.md` looks fully static (protocol v2 documentation).
4. **Multi-session caching** — the prompt cache TTL is short; even if
   `instructions` were re-sent across sessions, the savings within a
   session still dominates.
5. **First-call discoverability** — if a fresh client connects mid-conversation
   and missed the instructions, it won't know the protocol. This is the
   same trade-off as any "load once" optimization.

## Verification approach

1. Add a test in `tests/test_registry.py` asserting that `mcp.instructions`
   contains the expected protocol summary (built-in command names,
   pipeline operator list).
2. Add a test in `tests/test_handlers.py` asserting that
   `handle_standard_prompt` no longer includes the `PAL Protocol`
   header by default — only command body + user input.
3. Manual smoke: run `$$init-session` against the dev server, confirm
   the response body shrank by ~500 tokens.

## Expected savings

- Per prompt-based call: ~500 tokens.
- Typical session (5-10 prompt commands): 2.5K-5K tokens.
- Token budget reclaimed scales linearly with session length, so the
  benefit grows with longer interactions.

## Out of scope (potential follow-ups)

- Trimming `root.md` itself for further savings.
- Deduplicating the re-broadcast of MCP server instructions on
  reconnection (harness-level concern, not PAL's).
- Caching `list_pal_commands` results.
