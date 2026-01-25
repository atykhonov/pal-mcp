# PAL Setup

## Add MCP to Claude Code

```bash
claude mcp add pal --transport sse --url http://localhost:8090/sse
```

## Shell Alias

Add to `~/.bashrc` or `~/.zshrc`:

```bash
alias cc='claude -- "\$\$init-session"'
```
