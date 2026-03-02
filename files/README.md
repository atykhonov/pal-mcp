# PAL Setup

## Add MCP to Claude Code

```bash
claude mcp add pal --transport sse http://192.168.11.102:8090/sse
```

## Shell Alias

Add to `~/.bashrc` or `~/.zshrc`:

```bash
alias cc='claude -- "\$\$init-session"'
```

## Install JavaScript Bun

```bash
curl -fsSL https://bun.sh/install | bash
```
