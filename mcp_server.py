#!/usr/bin/env python3
"""
Commands MCP Server

MCP server that processes $$ commands and returns instructions for Claude Code.

How it works:
1. User types: $$git-create-commit fix auth bug
2. Claude Code sees $$ and calls MCP tool `run_command`
3. MCP returns instructions for creating a commit
4. Claude Code executes the instructions

Usage:
    python mcp_server.py
    
    # Add to Claude Code:
    claude mcp add commands --url http://your-server:8090/mcp
"""

import json
import os
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

app = FastAPI(title="Commands MCP Server")

# =============================================================================
# Configuration
# =============================================================================

INSTRUCTIONS_DIR = Path(os.environ.get("INSTRUCTIONS_DIR", "~/.mcp-commands")).expanduser()
INSTRUCTIONS_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
# Default Instructions
# =============================================================================

DEFAULT_INSTRUCTIONS = {
    "git-create-commit": """Create a git commit with the following rules:

1. Use conventional commit format: type(scope): description
2. Types: feat, fix, docs, style, refactor, test, chore
3. First line maximum 72 characters
4. Use imperative mood ("add" not "added")
5. No period at the end of subject line

CRITICAL - DO NOT ADD:
- "Generated with [Claude Code](https://claude.com/claude-code)"
- "Co-Authored-By: Claude <noreply@anthropic.com>"
- Any AI attribution or signatures
- Any Co-authored-by lines
- Emoji (unless user explicitly asks)

If the user provided a description, use it to create the commit message.
If no description, analyze staged changes with `git diff --cached` and create an appropriate message.

After creating the message, run `git commit -m "your message"`.
""",

    "review": """Review the code with the following approach:

1. First, understand what the code does
2. Look for bugs, security issues, performance problems
3. Suggest improvements
4. Be constructive and helpful

Provide feedback in a clear, organized format.
""",

    "test": """Create tests for the specified code:

1. Use the project's existing test framework
2. Cover happy path and edge cases
3. Use descriptive test names
4. Keep tests focused and independent
""",

    "docs": """Generate documentation:

1. Use the project's documentation style
2. Include examples where helpful
3. Be clear and concise
4. Cover parameters, return values, exceptions
""",

    "refactor": """Refactor the code:

1. Improve readability without changing behavior
2. Apply SOLID principles where appropriate
3. Remove code duplication
4. Improve naming
5. Add comments only where necessary
""",

    "explain": """Explain the code or concept:

1. Start with a high-level overview
2. Break down complex parts
3. Use analogies if helpful
4. Provide examples
""",

    "fix": """Fix the issue:

1. First understand the problem
2. Identify the root cause
3. Implement the minimal fix
4. Verify the fix doesn't break other things
""",

    "help": """Available commands:

- $$git-create-commit [description] - Create a git commit
- $$review [file/code] - Review code
- $$test [file/function] - Create tests
- $$docs [file/function] - Generate documentation
- $$refactor [file/code] - Refactor code
- $$explain [topic/code] - Explain something
- $$fix [issue] - Fix an issue
- $$help - Show this help

You can also create custom commands by adding .md files to the instructions directory.
""",
}

def ensure_default_instructions():
    for name, content in DEFAULT_INSTRUCTIONS.items():
        filepath = INSTRUCTIONS_DIR / f"{name}.md"
        if not filepath.exists():
            filepath.write_text(content)

ensure_default_instructions()

# =============================================================================
# Instructions Loader
# =============================================================================

def load_instruction(command: str) -> str:
    filepath = INSTRUCTIONS_DIR / f"{command}.md"
    if filepath.exists():
        return filepath.read_text(encoding='utf-8')

    if command in DEFAULT_INSTRUCTIONS:
        return DEFAULT_INSTRUCTIONS[command]
    
    return f"Unknown command: {command}\n\nUse $$help to see available commands."


def list_commands() -> list[str]:
    """Returns a list of available commands."""
    commands = set(DEFAULT_INSTRUCTIONS.keys())
    
    # Add commands from files
    for filepath in INSTRUCTIONS_DIR.glob("*.md"):
        commands.add(filepath.stem)
    
    return sorted(commands)

# =============================================================================
# MCP Protocol
# =============================================================================

TOOLS = [
    {
        "name": "run_command",
        "description": """Execute a $$ command and get instructions. 

Call this when user's message starts with $$ followed by a command name.

Examples:
- User: "$$git-create-commit fix auth bug" → call run_command(command="commit", args="fix auth bug")
- User: "$$review" → call run_command(command="review", args="")
- User: "$$help" → call run_command(command="help", args="")""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Command name (without $$). E.g., 'commit', 'review', 'help'"
                },
                "args": {
                    "type": "string",
                    "description": "Arguments passed after the command",
                    "default": ""
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "list_commands",
        "description": "List all available $$ commands",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_time",
        "description": "Get current server time",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]


def handle_initialize(request_id, params):
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "serverInfo": {
                "name": "commands-mcp",
                "version": "0.2.0"
            },
            "capabilities": {
                "tools": {}
            }
        }
    }


def handle_tools_list(request_id):
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "tools": TOOLS
        }
    }


def handle_tools_call(request_id, params):
    tool_name = params.get("name")
    arguments = params.get("arguments", {})
    
    if tool_name == "run_command":
        command = arguments.get("command", "").lower().strip()
        args = arguments.get("args", "").strip()
        
        instruction = load_instruction(command)
        
        if args:
            response_text = f"""# Command: $${command}
# Arguments: {args}

{instruction}

---
User's input: {args}
"""
        else:
            response_text = f"""# Command: $${command}

{instruction}
"""
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [{"type": "text", "text": response_text}]
            }
        }
    
    elif tool_name == "list_commands":
        commands = list_commands()
        response_text = "Available commands:\n\n" + "\n".join(f"- $${cmd}" for cmd in commands)
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [{"type": "text", "text": response_text}]
            }
        }
    
    elif tool_name == "get_time":
        now = datetime.now()
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [{"type": "text", "text": f"Server time: {now.strftime('%Y-%m-%d %H:%M:%S')}"}]
            }
        }
    
    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
        }


def process_message(message: dict) -> dict | None:
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params", {})
    
    if request_id is None:
        return None
    
    if method == "initialize":
        return handle_initialize(request_id, params)
    elif method == "tools/list":
        return handle_tools_list(request_id)
    elif method == "tools/call":
        return handle_tools_call(request_id, params)
    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"}
        }

# =============================================================================
# Static Files
# =============================================================================

FILES_DIR = Path(os.environ.get("FILES_DIR", "~/.mcp-commands/files")).expanduser()
FILES_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_FILES = {
    "CLAUDE.md": (
        Path(__file__).parent / "files" / "CLAUDE.md"
    ).read_text(encoding="utf-8"),
}


def ensure_default_files():
    """Creates default files."""
    for filename, content in DEFAULT_FILES.items():
        filepath = FILES_DIR / filename
        if not filepath.exists():
            filepath.write_text(content)

ensure_default_files()


@app.get("/files/{filename:path}")
async def get_file(filename: str):
    """
    Returns file content.
    
    Usage:
        curl http://server:8090/files/CLAUDE.md > CLAUDE.md
    """
    filepath = FILES_DIR / filename
    
    if not filepath.exists():
        return Response(
            content=f"File not found: {filename}",
            status_code=404,
            media_type="text/plain"
        )
    
    # Security: check that path does not go outside FILES_DIR
    try:
        filepath.resolve().relative_to(FILES_DIR.resolve())
    except ValueError:
        return Response(
            content="Access denied",
            status_code=403,
            media_type="text/plain"
        )
    
    content = filepath.read_text(encoding='utf-8')
    return Response(content=content, media_type="text/plain; charset=utf-8")


@app.get("/files")
async def list_files():
    """List of available files."""
    files = [f.name for f in FILES_DIR.iterdir() if f.is_file()]
    return {"files": files, "directory": str(FILES_DIR)}


# =============================================================================
# HTTP Endpoints
# =============================================================================

@app.post("/mcp")
@app.post("/message")
async def mcp_endpoint(request: Request):
    """JSON-RPC endpoint for MCP."""
    body = await request.json()
    response = process_message(body)
    return JSONResponse(response or {"jsonrpc": "2.0", "result": None})


@app.get("/")
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "server": "commands-mcp",
        "version": "0.2.0",
        "commands": list_commands(),
        "instructions_dir": str(INSTRUCTIONS_DIR)
    }


@app.get("/commands")
async def get_commands():
    commands = {}
    for cmd in list_commands():
        instruction = load_instruction(cmd)
        preview = instruction.strip().split('\n')[0][:100]
        commands[cmd] = preview
    return {"commands": commands}


@app.get("/command/{name}")
async def get_command(name: str):
    instruction = load_instruction(name)
    return {"command": name, "instruction": instruction}

# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("Commands MCP Server")
    print("=" * 60)
    print(f"Instructions directory: {INSTRUCTIONS_DIR}")
    print()
    print("Available commands:")
    for cmd in list_commands():
        print(f"  $${cmd}")
    print()
    print("Setup:")
    print("  1. Add MCP to Claude Code:")
    print("     claude mcp add commands --url http://your-server:8090/mcp")
    print()
    print("  2. Add to ~/.claude/CLAUDE.md:")
    print('     When you see a message starting with $$, call the')
    print('     run_command tool with the command name and arguments.')
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8090)

