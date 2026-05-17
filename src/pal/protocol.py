"""PAL protocol instructions surfaced to MCP clients.

This module exports `PROTOCOL_INSTRUCTIONS`: the static Markdown describing
the PAL command protocol. By default it is shipped once via FastMCP's
`instructions` field during the `initialize` handshake; opt-in modes (see
`PAL_PROTOCOL_HEADER_LOCATION` in `pal.config`) can also prepend it per-call
for harnesses that don't surface server instructions to the model.

Previously this content lived in `src/pal/prompts/bundled/root.md` and was
prepended to every `handle_standard_prompt` response (several hundred tokens
per call; see the design brief for measurement).
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
