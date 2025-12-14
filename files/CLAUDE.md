# Global Claude Code Instructions

## $$ Commands

When you see a message starting with `$$`:

1. Extract command name (first word after $$) and args (rest)

2. Check for LOCAL instructions in current project:
   - `.pal/commands/<command>.md` — full override
   - `.pal/commands/<command>.extend.md` — extension

3. Execute based on what exists:

   a) If `.pal/commands/<command>.md` exists:
      → Read and follow ONLY local instructions (ignore MCP)

   b) If `.pal/commands/<command>.extend.md` exists:
      → Call MCP tool `run_command` to get default instructions
      → Read local `.extend.md` file
      → Follow BOTH: MCP defaults + local extensions

   c) If neither exists:
      → Call MCP tool `run_command` for default instructions

Example: `$$commit fix auth bug`
- command = "commit"
- args = "fix auth bug"
- Check .pal/commands/commit.md → if exists, use it
- Else check .pal/commands/commit.extend.md → if exists, combine with MCP
- Else call run_command(command="commit", args="fix auth bug")

