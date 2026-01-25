# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PAL (Personal AI Layer) is an MCP server that enables LLMs to execute custom commands via `$$command` syntax. It provides prompt management, command pipelines, variable substitution, and optional Meilisearch-backed notes with AI tagging.

## Development Commands

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run server
pal                          # CLI entry point (SSE mode, port 8090)
PAL_TRANSPORT=stdio pal      # stdio mode for direct integration

# Tests
pytest                       # all tests
pytest tests/test_parser.py  # single file
pytest -k "test_parse"       # by name pattern

# Code quality
black src tests              # format
ruff check src tests         # lint
ruff check --fix src tests   # lint with autofix
mypy src                     # type check

# Docker (includes Meilisearch + Ollama)
docker compose up --build -d
```

## Architecture

### Core Flow

1. **Server** (`server.py`) — ASGI app handling MCP over SSE/Streamable HTTP, OAuth 2.0, and static files
2. **Tools** (`tools/registry.py`) — Registers MCP tools: `run_pal_command`, `list_pal_commands`, `pal_curl`, and resource handlers
3. **Prompts** (`prompts/loader.py`) — Three-tier prompt loading: bundled → user (`~/.pal-mcp-prompts/`) → custom (`~/.pal-mcp-prompts/custom/`)

### MCP Tools

| Tool | Purpose |
|------|---------|
| `run_pal_command` | Execute `$$command` — returns bundled prompts for LLM to follow |
| `list_pal_commands` | List available commands |
| `pal_curl` | Execute curl commands server-side (used by notes, tags) |
| `read_pal_resource` / `list_pal_resources` | Access prompt files as MCP resources |

### Prompt System

Prompts are markdown files with optional YAML frontmatter. Loading priority:

1. **User prompts** (`~/.pal-mcp-prompts/command.md`) — can override or merge with bundled
2. **Bundled prompts** (`src/pal/prompts/bundled/`) — shipped with package
3. **Custom prompts** (`~/.pal-mcp-prompts/custom/`) — user-created via `$$prompt`

Frontmatter `merge_strategy`: `override` (default), `append`, `prepend`

### Key Files

- `src/pal/server.py` — MCPApp ASGI class, transport handling, OAuth endpoints
- `src/pal/config.py` — Settings via pydantic-settings, all `PAL_*` env vars
- `src/pal/tools/registry.py` — Tool registration and handlers
- `src/pal/tools/handlers.py` — Command execution logic (built-ins: echo, prompt, help)
- `src/pal/prompts/loader.py` — Prompt loading, merging, and listing
- `src/pal/prompts/bundled/root.md` — Protocol instructions sent with every command response

### Configuration

All settings via `PAL_*` environment variables (see `config.py`):
- `PAL_TRANSPORT` — `sse` (default) or `stdio`
- `PAL_SERVER_PORT` — default 8090
- `PAL_PROMPTS_DIR` — default `~/.pal-mcp-prompts`
- `PAL_MEILISEARCH_URL` — enables notes feature
- `PAL_NOTES_AI_PROVIDER` — `pal-follow-up`, `ollama`, `mcp-sampling`, or `none`

## Code Patterns

- **Async handlers** — Tool handlers in registry.py are async, use `request_ctx.get()` for MCP session access
- **Type hints** — Strict mypy enabled, use `from __future__ import annotations`
- **Tests** — pytest-asyncio with `asyncio_mode = "auto"`, fixtures in `conftest.py`
