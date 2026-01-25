# PAL Local Overrides

When you see `$$<command> [subcommand]`, check for local prompt first:
- `$$git commit` → `.pal-mcp-prompts/git/commit.md`
- `$$notes` → `.pal-mcp-prompts/notes.md`

If local file exists, check its YAML frontmatter for `merge_strategy`:
- `override` (default) — follow local only, skip MCP
- `append` — call `run_pal_command`, then apply local after
- `prepend` — call `run_pal_command`, apply local before

If no local file exists, call `run_pal_command` with the command.

