# PAL Setup

## Install Claude Code
```bash
curl -fsSL https://claude.ai/install.sh | bash
```

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

## Install Serena MCP

```bash
claude mcp add --scope user serena -- \
  uvx --from git+https://github.com/oraios/serena \
  serena start-mcp-server --context claude-code --project-from-cwd

curl -LsSf https://astral.sh/uv/install.sh | sh
uvx --from git+https://github.com/oraios/serena serena project index

```
