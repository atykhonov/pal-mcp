# FastMCP + Starlette Migration Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate PAL from the low-level MCP `Server` API to `FastMCP` with decorator-based tools, and replace the raw ASGI `MCPApp` with a Starlette app that mounts FastMCP's built-in transport apps.

**Architecture:** Create a `FastMCP` instance in `registry.py` with `@mcp.tool()` decorators replacing manual `inputSchema` dicts and dispatch logic. In `server.py`, replace the custom `MCPApp` ASGI class with a Starlette app that mounts `mcp.sse_app()` and `mcp.streamable_http_app()` for transport, keeps OAuth as Starlette route handlers, and wraps MCP routes with auth middleware.

**Tech Stack:** `mcp>=1.27.0`, `starlette` (transitive via mcp), `FastMCP`, `uvicorn`

---

### Task 1: Upgrade MCP dependency

**Files:**
- Modify: `pyproject.toml:27`

**Step 1: Update the mcp version constraint**

In `pyproject.toml`, change line 27:
```
"mcp>=1.0.0",
```
to:
```
"mcp>=1.27.0",
```

**Step 2: Reinstall the package**

Run: `pip install -e ".[dev]"`
Expected: installs mcp 1.27.x successfully

**Step 3: Verify**

Run: `python -c "import mcp; print(mcp.__version__)"`
Expected: `1.27.x`

**Step 4: Run existing tests to establish baseline**

Run: `pytest`
Expected: all tests pass

**Step 5: Commit**

```bash
git add pyproject.toml
git commit -m "chore: upgrade mcp dependency to >=1.27.0"
```

---

### Task 2: Rewrite registry.py with FastMCP tool decorators

**Files:**
- Rewrite: `src/pal/tools/registry.py`
- Modify: `src/pal/tools/__init__.py`

**Step 1: Rewrite `src/pal/tools/registry.py`**

Replace the entire file with FastMCP-based tool registration. Key changes:
- Create `FastMCP("pal-server", instructions=...)` instance at module level
- Replace `register_tools(server)` function with `@mcp.tool()` decorated functions
- Tools return `str` instead of `list[types.TextContent]`
- `run_pal_command` gets `ctx: Context` injected by FastMCP, passes `ctx.request_context` to `execute_command()`
- `pal_curl` is sync (matching `execute_curl`)
- Remove all manual `inputSchema` dicts and `call_tool` dispatch

```python
"""MCP tool registration using FastMCP."""

from __future__ import annotations

import json

from mcp.server.fastmcp import Context, FastMCP

from pal.config import get_settings
from pal.prompts import (
    list_available_commands,
    list_custom_prompts,
    load_custom_prompt,
    load_prompt,
)
from pal.tools.curl import execute_curl
from pal.tools.handlers import execute_command
from pal.tools.parser import parse_command

SERVER_INSTRUCTIONS = (
    "When you see $$ at the start of user input, "
    "call run_pal_command with the command text."
)

mcp = FastMCP("pal-server", instructions=SERVER_INSTRUCTIONS)


@mcp.tool()
async def run_pal_command(command: str, ctx: Context) -> str:
    """Execute a PAL $$ command. For built-in commands (echo, prompt, help): executes and returns result. For prompt-based commands: returns bundled prompts for you to follow."""
    command = command.strip()
    if not command:
        return "Error: No command provided"

    print(f"[TOOL] Executing run_pal_command...")
    parsed = parse_command(command)
    return await execute_command(parsed, ctx.request_context)


@mcp.tool()
async def list_pal_commands() -> str:
    """List all available $$ commands."""
    print("[TOOL] Executing list_pal_commands...")
    commands = list_available_commands()
    return f"Commands: {', '.join(commands)}"


@mcp.tool()
async def read_pal_resource(uri: str) -> str:
    """Read PAL resource files (prompt definitions). Returns the content of the specified prompt file."""
    uri = uri.strip()
    if not uri:
        return "Error: URI is required"

    print("[TOOL] Executing read_pal_resource...")
    content: str | None = None

    if uri.startswith("pal://prompts/custom/"):
        name = uri[len("pal://prompts/custom/") :].removesuffix(".md")
        content = load_custom_prompt(name)
    elif uri.startswith("pal://prompts/"):
        rel_path = uri[len("pal://prompts/") :]
        parts = rel_path.removesuffix(".md").split("/")
        if len(parts) == 1:
            content = load_prompt(parts[0])
            if content.startswith("Unknown command:"):
                content = None
        elif len(parts) == 2:
            content = load_prompt(parts[0], parts[1])
            if content.startswith("Unknown command:"):
                content = None
        else:
            settings = get_settings()
            file_path = settings.prompts_path / rel_path
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")

    if content is None:
        return f"Error: Resource not found: {uri}"
    return content


@mcp.tool()
async def list_pal_resources() -> str:
    """List all available PAL prompt resources. Returns URIs that can be used with read_pal_resource."""
    print("[TOOL] Executing list_pal_resources...")
    resources: list[str] = []
    settings = get_settings()

    prompts_path = settings.prompts_path
    if prompts_path.exists():
        for path in sorted(prompts_path.rglob("*.md")):
            rel_path = path.relative_to(prompts_path)
            if rel_path.parts and rel_path.parts[0] == "custom":
                continue
            resources.append(f"pal://prompts/{rel_path}")

    for name in list_custom_prompts():
        resources.append(f"pal://prompts/custom/{name}.md")

    return "Available resources:\n" + "\n".join(f"  - {r}" for r in resources)


@mcp.tool()
def pal_curl(command: str, timeout: int = 30) -> str:
    """Execute a curl command on the server. Pass the full curl command string (e.g., 'curl -s http://localhost:7700/health'). All standard curl flags are supported. Returns JSON with 'success', 'output', and optionally 'error'."""
    print("[TOOL] Executing pal_curl...")
    result = execute_curl(command=command, timeout=timeout)
    return json.dumps(result, indent=2)
```

**Step 2: Update `src/pal/tools/__init__.py`**

Replace the file to export the `mcp` instance instead of `register_tools`:

```python
"""Tools module for MCP tool definitions and command handling."""

from pal.tools.parser import parse_command
from pal.tools.registry import mcp

__all__ = [
    "mcp",
    "parse_command",
]
```

**Step 3: Run existing tests**

Run: `pytest tests/test_handlers.py tests/test_parser.py -v`
Expected: all pass (handlers and parser are unchanged)

**Step 4: Commit**

```bash
git add src/pal/tools/registry.py src/pal/tools/__init__.py
git commit -m "refactor(tools): migrate to FastMCP decorator-based tool registration"
```

---

### Task 3: Write test for FastMCP tool registration

**Files:**
- Create: `tests/test_registry.py`

**Step 1: Write the test**

```python
"""Tests for FastMCP tool registration."""

from __future__ import annotations

from pal.tools.registry import mcp


class TestToolRegistration:
    """Verify all tools are registered on the FastMCP instance."""

    def test_mcp_instance_exists(self) -> None:
        """FastMCP instance is created with correct name."""
        assert mcp.name == "pal-server"

    def test_all_tools_registered(self) -> None:
        """All 5 tools are registered."""
        tool_names = {name for name in mcp._tool_manager._tools}
        expected = {
            "run_pal_command",
            "list_pal_commands",
            "read_pal_resource",
            "list_pal_resources",
            "pal_curl",
        }
        assert expected == tool_names

    def test_run_pal_command_schema(self) -> None:
        """run_pal_command has correct input schema."""
        tool = mcp._tool_manager._tools["run_pal_command"]
        schema = tool.parameters
        assert "command" in schema.get("properties", {})
        assert "command" in schema.get("required", [])

    def test_pal_curl_has_timeout_default(self) -> None:
        """pal_curl has timeout parameter with default."""
        tool = mcp._tool_manager._tools["pal_curl"]
        schema = tool.parameters
        props = schema.get("properties", {})
        assert "command" in props
        assert "timeout" in props

    def test_server_instructions(self) -> None:
        """Server instructions are set."""
        assert "$$" in (mcp.instructions or "")
```

**Step 2: Run the test**

Run: `pytest tests/test_registry.py -v`
Expected: all pass

Note: The `_tool_manager._tools` is a FastMCP internal. If it fails due to API changes, inspect the `mcp` object to find where tools are stored:
```python
python -c "from pal.tools.registry import mcp; print(dir(mcp))"
```

**Step 3: Commit**

```bash
git add tests/test_registry.py
git commit -m "test(tools): add FastMCP tool registration tests"
```

---

### Task 4: Rewrite server.py with Starlette + mounted FastMCP transports

**Files:**
- Rewrite: `src/pal/server.py`

This is the largest task. The new server.py replaces the raw ASGI `MCPApp` class with:
- A Starlette app with route handlers for OAuth
- FastMCP's `sse_app()` and `streamable_http_app()` mounted at the right paths
- An ASGI auth middleware wrapping the MCP transport routes
- File serving via Starlette route

**Step 1: Rewrite `src/pal/server.py`**

```python
"""MCP Server implementation using FastMCP + Starlette."""

from __future__ import annotations

import asyncio
import contextlib
import json
from typing import Any
from urllib.parse import parse_qs, urlencode

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.routing import Mount, Route

from pal.config import Settings, get_settings, setup_logging
from pal.oauth import OAuthManager, get_oauth_manager
from pal.prompts import ensure_defaults
from pal.tools import mcp


class AuthMiddleware:
    """ASGI middleware that enforces OAuth/IP-based authentication."""

    def __init__(
        self, app: Any, oauth: OAuthManager, settings: Settings
    ) -> None:
        self.app = app
        self.oauth = oauth
        self.settings = settings

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if not self._is_authenticated(scope):
            client_ip, _ = self._get_client_ip(scope)
            print(f"[AUTH] Unauthorized from {client_ip}")
            response = Response(
                "Authentication required",
                status_code=401,
                headers={"www-authenticate": "Bearer"},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)

    def _is_authenticated(self, scope: dict) -> bool:
        token = self._get_bearer_token(scope)
        if token and self.oauth.validate_token(token):
            return True
        client_ip, is_proxied = self._get_client_ip(scope)
        if not is_proxied and self.oauth.is_ip_allowed(client_ip):
            return True
        return False

    def _get_bearer_token(self, scope: dict) -> str | None:
        for name, value in scope.get("headers", []):
            if name == b"authorization":
                auth = value.decode()
                if auth.startswith("Bearer "):
                    return auth[7:]
        return None

    def _get_client_ip(self, scope: dict) -> tuple[str, bool]:
        for name, value in scope.get("headers", []):
            if name in (b"x-forwarded-for", b"x-real-ip"):
                return value.decode().split(",")[0].strip(), True
        client = scope.get("client")
        if client:
            return client[0], False
        return "", False


def _create_oauth_routes(
    oauth: OAuthManager, settings: Settings
) -> list[Route]:
    """Create Starlette routes for OAuth endpoints."""

    async def oauth_metadata(request: Request) -> JSONResponse:
        return JSONResponse(oauth.get_metadata())

    async def protected_resource_metadata(request: Request) -> JSONResponse:
        base_url = (
            settings.oauth_public_url
            or f"http://localhost:{settings.server_port}"
        )
        return JSONResponse(
            {
                "resource": base_url,
                "authorization_servers": [base_url],
            }
        )

    async def handle_register(request: Request) -> JSONResponse:
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return JSONResponse(
                {"error": "invalid_request", "error_description": "Invalid JSON body"},
                status_code=400,
            )
        client_name = data.get("client_name", "Unknown Client")
        redirect_uris = data.get("redirect_uris", [])
        if not redirect_uris:
            return JSONResponse(
                {
                    "error": "invalid_request",
                    "error_description": "redirect_uris is required",
                },
                status_code=400,
            )
        client = oauth.register_client(client_name, redirect_uris)
        return JSONResponse(
            {
                "client_id": client.client_id,
                "client_name": client.client_name,
                "redirect_uris": client.redirect_uris,
            },
            status_code=201,
        )

    async def handle_authorize(request: Request) -> Response:
        params = dict(request.query_params)
        client_id = params.get("client_id", "")
        redirect_uri = params.get("redirect_uri", "")
        response_type = params.get("response_type", "")
        state = params.get("state", "")
        code_challenge = params.get("code_challenge", "")
        code_challenge_method = params.get("code_challenge_method", "S256")

        if response_type != "code":
            return JSONResponse(
                {
                    "error": "unsupported_response_type",
                    "error_description": "Only 'code' is supported",
                },
                status_code=400,
            )
        if not code_challenge:
            return JSONResponse(
                {
                    "error": "invalid_request",
                    "error_description": "code_challenge required (PKCE)",
                },
                status_code=400,
            )
        if not oauth.get_client(client_id):
            oauth.register_client(f"Auto: {client_id}", [redirect_uri])
        if not oauth.validate_redirect_uri(client_id, redirect_uri):
            return JSONResponse(
                {
                    "error": "invalid_request",
                    "error_description": "Invalid redirect_uri",
                },
                status_code=400,
            )
        code = oauth.create_authorization_code(
            client_id=client_id,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
        )
        redirect_params: dict[str, str] = {"code": code}
        if state:
            redirect_params["state"] = state
        redirect_url = f"{redirect_uri}?{urlencode(redirect_params)}"
        print(f"[OAUTH] Redirecting to: {redirect_url}")
        return RedirectResponse(redirect_url, status_code=302)

    async def handle_token(request: Request) -> JSONResponse:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                data = await request.json()
            except json.JSONDecodeError:
                return JSONResponse(
                    {"error": "invalid_request", "error_description": "Invalid JSON"},
                    status_code=400,
                )
        else:
            body = await request.body()
            data = {k: v[0] for k, v in parse_qs(body.decode()).items()}

        grant_type = data.get("grant_type", "")
        if grant_type != "authorization_code":
            return JSONResponse(
                {
                    "error": "unsupported_grant_type",
                    "error_description": "Only authorization_code supported",
                },
                status_code=400,
            )
        code = data.get("code", "")
        client_id = data.get("client_id", "")
        redirect_uri = data.get("redirect_uri", "")
        code_verifier = data.get("code_verifier", "")
        if not all([code, client_id, code_verifier]):
            return JSONResponse(
                {
                    "error": "invalid_request",
                    "error_description": "Missing required parameters",
                },
                status_code=400,
            )
        access_token = oauth.exchange_code(
            code, client_id, redirect_uri, code_verifier
        )
        if not access_token:
            return JSONResponse(
                {
                    "error": "invalid_grant",
                    "error_description": "Invalid code or verifier",
                },
                status_code=400,
            )
        return JSONResponse(
            {
                "access_token": access_token.token,
                "token_type": "Bearer",
                "expires_in": access_token.expires_in,
            }
        )

    return [
        Route(
            "/.well-known/oauth-authorization-server",
            oauth_metadata,
            methods=["GET"],
        ),
        Route(
            "/.well-known/oauth-protected-resource",
            protected_resource_metadata,
            methods=["GET"],
        ),
        Route("/register", handle_register, methods=["POST"]),
        Route("/authorize", handle_authorize, methods=["GET"]),
        Route("/token", handle_token, methods=["POST"]),
    ]


def _create_file_route(settings: Settings) -> Route:
    """Create Starlette route for static file serving."""

    async def handle_files(request: Request) -> Response:
        path = request.path_params["path"]
        filepath = settings.files_path / path
        if filepath.exists():
            return Response(
                filepath.read_bytes(), media_type="text/plain"
            )
        return Response("Not Found", status_code=404)

    return Route("/files/{path:path}", handle_files, methods=["GET"])


def create_app(settings: Settings | None = None) -> Starlette:
    """Create the Starlette ASGI application.

    Mounts FastMCP transport apps with auth middleware,
    OAuth endpoints, and static file serving.
    """
    if settings is None:
        settings = get_settings()

    oauth = get_oauth_manager(settings)

    # Configure FastMCP transport paths
    mcp.settings.streamable_http_path = "/"

    # Wrap MCP transports with auth
    authed_streamable = AuthMiddleware(
        mcp.streamable_http_app(), oauth, settings
    )
    authed_sse = AuthMiddleware(mcp.sse_app(), oauth, settings)

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette):
        async with mcp.session_manager.run():
            yield

    routes: list[Route | Mount] = [
        # OAuth (unauthenticated)
        *_create_oauth_routes(oauth, settings),
        # Static files (unauthenticated)
        _create_file_route(settings),
        # MCP Streamable HTTP (authenticated)
        Mount("/mcp", app=authed_streamable),
        # MCP SSE (authenticated) - handles /sse GET + /messages POST
        Mount("/", app=authed_sse),
    ]

    return Starlette(routes=routes, lifespan=lifespan)


async def run_stdio_server(settings: Settings) -> None:
    """Run the MCP server with stdio transport."""
    async with mcp.session_manager.run():
        await mcp.run(transport="stdio")


def run_sse_server(settings: Settings) -> None:
    """Run the MCP server with SSE/Streamable HTTP transport."""
    app = create_app(settings)

    protocol = "https" if settings.ssl_certfile else "http"
    print("=" * 60)
    print("PAL MCP SERVER")
    print(f"Listening on {protocol}://{settings.server_host}:{settings.server_port}")
    print("=" * 60)

    ssl_kwargs: dict[str, Any] = {}
    if settings.ssl_certfile and settings.ssl_keyfile:
        ssl_kwargs["ssl_certfile"] = str(settings.ssl_certfile.expanduser())
        ssl_kwargs["ssl_keyfile"] = str(settings.ssl_keyfile.expanduser())

    uvicorn.run(
        app,
        host=settings.server_host,
        port=settings.server_port,
        **ssl_kwargs,
    )


def run_server(settings: Settings | None = None) -> None:
    """Run the MCP server."""
    if settings is None:
        settings = get_settings()

    setup_logging(settings)
    ensure_defaults()

    if settings.transport == "stdio":
        asyncio.run(run_stdio_server(settings))
    else:
        run_sse_server(settings)


if __name__ == "__main__":
    run_server()
```

**Step 2: Run existing tests**

Run: `pytest -v`
Expected: all existing tests pass (none test server.py directly)

**Step 3: Commit**

```bash
git add src/pal/server.py
git commit -m "refactor(server): replace raw ASGI MCPApp with Starlette + FastMCP transports"
```

---

### Task 5: Smoke test the running server

**Step 1: Start the server in background**

Run: `PAL_SERVER_PORT=18090 timeout 10 pal &`
Expected: prints "PAL MCP SERVER" banner, starts listening

**Step 2: Test OAuth metadata endpoint**

Run: `curl -s http://localhost:18090/.well-known/oauth-authorization-server | python3 -m json.tool`
Expected: JSON with `issuer`, `authorization_endpoint`, etc.

**Step 3: Test SSE endpoint responds**

Run: `curl -s -N -H "Accept: text/event-stream" http://localhost:18090/sse --max-time 3 2>/dev/null | head -5`
Expected: SSE event stream data (e.g., `event: endpoint` message)

**Step 4: Test Streamable HTTP endpoint**

Run: `curl -s -X POST http://localhost:18090/mcp -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}' --max-time 3 | head -5`
Expected: JSON-RPC response or SSE event with initialization result

**Step 5: Test file serving**

Run: `mkdir -p ~/.pal-mcp-prompts/files && echo "test" > ~/.pal-mcp-prompts/files/test.txt && curl -s http://localhost:18090/files/test.txt`
Expected: `test`

**Step 6: Stop server and clean up**

Run: `kill %1 2>/dev/null; rm -f ~/.pal-mcp-prompts/files/test.txt`

---

### Task 6: Update type annotations in handlers (if needed)

**Files:**
- Possibly modify: `src/pal/tools/types.py`
- Possibly modify: `src/pal/tools/handlers.py`

After Task 4, check if the `RequestContext` type import still resolves correctly. The handler chain expects `RequestContext[ServerSession, object, object] | None` and `ctx.request_context` from FastMCP should provide this.

**Step 1: Run type checker**

Run: `mypy src/pal/tools/registry.py src/pal/server.py`

If there are type errors, fix them. Common fixes:
- FastMCP `Context.request_context` might have a different generic signature
- Starlette types may need `# type: ignore` for strict mypy

**Step 2: Run full type check**

Run: `mypy src`

Fix any remaining issues. The mypy config already has `ignore_missing_imports = true` for `mcp.*` and `uvicorn.*`.

**Step 3: Run linter**

Run: `ruff check src --fix && black src`

**Step 4: Run all tests**

Run: `pytest -v`
Expected: all pass

**Step 5: Commit any fixes**

```bash
git add -u
git commit -m "fix: resolve type and lint issues from FastMCP migration"
```

---

### Task 7: Final verification and commit

**Step 1: Run full test suite**

Run: `pytest -v`
Expected: all pass

**Step 2: Run all quality checks**

Run: `black --check src tests && ruff check src tests && mypy src`
Expected: all pass

**Step 3: Verify no regressions in tool behavior**

Run the server and test with an MCP client or `curl` that the tools respond correctly. Check that `$$help` returns the expected output when invoked through the MCP protocol.

---

## Migration notes

### What was removed
- `register_tools(server: Server)` function and all manual `inputSchema` dicts
- `call_tool()` dispatch chain with `if name ==` conditionals
- `MCPApp` raw ASGI class (~200 lines)
- Manual `StreamableHTTPServerTransport` session tracking
- Manual SSE/Streamable HTTP transport negotiation
- Raw ASGI helper methods (`_json_response`, `_read_body`, etc.)

### What was added
- `FastMCP` instance with 5 `@mcp.tool()` decorated functions
- `AuthMiddleware` ASGI class (~40 lines)
- Starlette route handlers for OAuth (~120 lines, same logic, cleaner API)
- `create_app()` factory function
- Lifespan context manager for session management

### Breaking changes
- None for MCP clients. Endpoints stay at `/sse`, `/messages`, `/mcp`
- Internal: `register_tools()` no longer exists, replaced by `mcp` module-level instance
