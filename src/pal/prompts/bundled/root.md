---
type: protocol
version: 2
---

# PAL Command Protocol

## Built-in Commands

These commands execute directly and return results:
- `$$echo <text>` - Echo text with variable substitution
- `$$prompt [name] [content]` - List/view/create custom prompts
- `$$help` - Show all available commands

## Variable Substitution

Available variables:
- `$MSG` - User's previous message
- `$REPLY` - Your previous response
- Heading variables: `## Summary` creates `$SUMMARY`

## Pipeline Operators

Commands can be chained:
- `|` (pipe) - Pass output as input to next command
- `&&` (and) - Run next only if current succeeds
- `;` (seq) - Run next regardless

Example: `$$notes search docker | summarize`

## Executing Prompt-Based Commands

When you receive bundled prompts (this response):
1. Read the Command and Subcommand sections below
2. Parse the User Input section for arguments and content
3. Execute using the curl tool as described in the prompts
4. Format output as specified in the prompts

## Error Handling

Report errors clearly with usage hints. Example:
```
Error: Missing required content
Usage: $$notes add [-t tags] <content>
```
