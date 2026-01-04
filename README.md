# PAL - Personal AI Layer

An MCP (Model Context Protocol) server for custom commands and prompt management. PAL enables LLMs like Claude to execute custom commands through a simple `$$command` syntax.

## Features

- **Custom Commands**: Define and execute custom prompts with `$$command` syntax
- **Command Pipelines**: Chain commands with `|` operator (`$$cmd1 | cmd2`)
- **Prompt Management**: Create, view, and manage custom prompts
- **Variable Substitution**: Use `$MSG`, `$REPLY`, and heading-based variables
- **Notes**: Full-text searchable notes with AI-powered tagging (requires Meilisearch)
- **OAuth 2.0**: Secure authentication with PKCE for external connections
- **Extensible**: Add custom instructions via filesystem or built-in defaults

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/atykhonov/pal-mcp.git
cd pal-mcp

# Install in development mode
pip install -e ".[dev]"
```

### Using Docker

```bash
docker compose up --build -d
```

## Quick Start

### Running the Server

```bash
# Using the CLI entry point
pal

# Or as a Python module
python -m pal

# Or directly
python src/pal/server.py
```

The server starts on `http://localhost:8090` by default.

### Configuration

PAL uses environment variables for configuration. You can also use a `.env` file in the project root.

#### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `PAL_TRANSPORT` | `sse` | Transport type: `sse` or `stdio` |
| `PAL_SERVER_PORT` | `8090` | Server port |
| `PAL_SERVER_HOST` | `0.0.0.0` | Server host |
| `PAL_INSTRUCTIONS_DIR` | `~/.mcp-commands` | Directory for instruction files |
| `PAL_FILES_DIR` | `~/.mcp-commands/files` | Directory for static files |
| `PAL_PROMPTS_DIR` | `./prompts` | Directory for custom prompts |
| `PAL_LOG_LEVEL` | `INFO` | Logging level |
| `PAL_SSL_CERTFILE` | - | Path to SSL certificate file |
| `PAL_SSL_KEYFILE` | - | Path to SSL key file |

#### OAuth Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `PAL_OAUTH_ENABLED` | `true` | Enable OAuth 2.0 for external connections |
| `PAL_OAUTH_PUBLIC_URL` | - | Public URL for OAuth redirects |
| `PAL_OAUTH_SECRET` | (generated) | Secret key for signing tokens |
| `PAL_OAUTH_TOKEN_EXPIRY` | `86400` | Token expiry in seconds (24 hours) |
| `PAL_OAUTH_ALLOWED_NETWORKS` | `127.0.0.0/8,...` | CIDR ranges that bypass OAuth |

#### Notes Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `PAL_NOTES_ENABLED` | `false` | Enable notes feature |
| `PAL_MEILISEARCH_URL` | - | Meilisearch URL (e.g., `http://localhost:7700`) |
| `PAL_NOTES_AI_PROVIDER` | `pal-follow-up` | AI provider for tag generation: `mcp-sampling`, `ollama`, `pal-follow-up`, or `none` |
| `PAL_OLLAMA_URL` | `http://localhost:11434` | Ollama URL for AI features |
| `PAL_OLLAMA_MODEL` | `llama3.2` | Ollama model for AI features |

## Usage

### Built-in Commands

| Command | Description |
|---------|-------------|
| `$$help` | List all available commands |
| `$$echo <text>` | Echo text (with variable substitution) |
| `$$lorem-ipsum` | Generate lorem ipsum text |
| `$$prompt` | List all custom prompts |
| `$$prompt <name>` | Show a prompt definition |
| `$$prompt <name> <instruction>` | Create/update a custom prompt |
| `$$<namespace> --help` | Show available subcommands |

### Notes Commands

Requires `PAL_NOTES_ENABLED=true` and a running Meilisearch instance.

| Command | Description |
|---------|-------------|
| `$$notes add <text>` | Add a new note with AI-generated tags |
| `$$notes list` | List all notes |
| `$$notes list --tags tag1,tag2` | List notes filtered by tags |
| `$$notes search <query>` | Full-text search notes |
| `$$notes search --ai <query>` | AI-powered semantic search |
| `$$notes view <id>` | View a note by ID |
| `$$notes tags <id>` | Regenerate tags for a note |
| `$$notes delete <id>` | Delete a note |

### Creating Custom Prompts

```bash
# Create a translation prompt
$$prompt tr Translate the following text to Ukrainian:\n\n{input}

# Use the prompt
$$tr Hello, world!
```

### Command Pipelines

```bash
# Chain commands together
$$echo Hello | tr
```

### Variable Substitution

The LLM automatically substitutes these variables before calling commands:

- `$MSG` - The user's previous message
- `$REPLY` - The LLM's previous response
- `$HEADING_NAME` - Content under `## Heading Name` in previous response

## Project Structure

```
pal-mcp/
├── src/pal/                    # Main package
│   ├── __init__.py
│   ├── __main__.py             # Entry point
│   ├── config.py               # Configuration (pydantic-settings)
│   ├── server.py               # MCP server with OAuth 2.0
│   ├── auth.py                 # OAuth 2.1 manager
│   ├── instructions/           # Instruction management
│   │   ├── __init__.py
│   │   ├── defaults.py         # Default instructions
│   │   └── loader.py           # Instruction loading
│   └── tools/                  # MCP tools
│       ├── __init__.py
│       ├── handlers.py         # Command handlers
│       ├── parser.py           # Command parsing
│       ├── registry.py         # Tool registration
│       └── notes.py            # Notes commands (Meilisearch)
├── tests/                      # Test suite
├── prompts/                    # Custom prompts directory
├── pyproject.toml              # Project configuration
├── Dockerfile
└── docker-compose.yml          # Includes Meilisearch & Ollama
```

## Development

### Setup

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Set up pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/pal --cov-report=html
```

### Code Quality

```bash
# Format code
black src tests

# Lint
ruff check src tests

# Type checking
mypy src
```

## Adding Custom Instructions

### Via Filesystem

Create `.md` files in `~/.mcp-commands/`:

```bash
# Flat command: ~/.mcp-commands/mycommand.md
echo "Your instruction here" > ~/.mcp-commands/mycommand.md

# Nested command: ~/.mcp-commands/namespace/subcommand.md
mkdir -p ~/.mcp-commands/git
echo "Git commit instructions" > ~/.mcp-commands/git/commit.md
```

### Via Prompts Directory

Create `.md` files in the `prompts/` directory of the project:

```bash
echo "Translate to Spanish:" > prompts/es.md
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sse` | GET | SSE connection for MCP |
| `/mcp` | POST | Streamable HTTP transport |
| `/authorize` | GET | OAuth 2.0 authorization |
| `/token` | POST | OAuth 2.0 token exchange |
| `/files/*` | GET | Static file serving |

## MCP Tools

PAL exposes two MCP tools:

### `run_pal_command`

Execute a PAL command with optional pipeline.

```json
{
  "command": "git commit | review"
}
```

### `list_pal_commands`

List all available commands.

## License

MIT
