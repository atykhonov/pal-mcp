# PAL - Personal AI Layer

An MCP (Model Context Protocol) server for custom commands and prompt management. PAL enables LLMs like Claude to execute custom commands through a simple `$$command` syntax.

## Features

- **Custom Commands**: Define and execute custom prompts with `$$command` syntax
- **Command Pipelines**: Chain commands with `|` operator (`$$cmd1 | cmd2`)
- **Prompt Management**: Create, view, and manage custom prompts
- **Variable Substitution**: Use `$MSG`, `$REPLY`, and heading-based variables
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
docker-compose up -d
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

PAL uses environment variables for configuration:

| Variable | Default | Description |
|----------|---------|-------------|
| `PAL_SERVER_PORT` | `8090` | Server port |
| `PAL_SERVER_HOST` | `0.0.0.0` | Server host |
| `PAL_INSTRUCTIONS_DIR` | `~/.mcp-commands` | Directory for instruction files |
| `PAL_FILES_DIR` | `~/.mcp-commands/files` | Directory for static files |
| `PAL_LOG_LEVEL` | `INFO` | Logging level |

You can also use a `.env` file in the project root.

## Usage

### Built-in Commands

| Command | Description |
|---------|-------------|
| `$$echo <text>` | Echo text (with variable substitution) |
| `$$lorem-ipsum` | Generate lorem ipsum text |
| `$$prompt` | List all custom prompts |
| `$$prompt <name>` | Show a prompt definition |
| `$$prompt <name> <instruction>` | Create/update a custom prompt |
| `$$<namespace> --help` | Show available subcommands |

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
│   ├── server.py               # MCP server
│   ├── instructions/           # Instruction management
│   │   ├── __init__.py
│   │   ├── defaults.py         # Default instructions
│   │   └── loader.py           # Instruction loading
│   └── tools/                  # MCP tools
│       ├── __init__.py
│       ├── handlers.py         # Command handlers
│       ├── parser.py           # Command parsing
│       └── registry.py         # Tool registration
├── tests/                      # Test suite
├── prompts/                    # Custom prompts directory
├── files/                      # Static files
├── pyproject.toml              # Project configuration
├── Dockerfile
└── docker-compose.yml
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
| `/sse` | GET | SSE connection handshake |
| `/messages` | POST | MCP message handling |
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
