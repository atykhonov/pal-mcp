"""Tests for the Starlette ASGI app: OAuth discovery and auth challenges."""

from __future__ import annotations

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from pal.config import Settings
from pal.server import create_app
from pal.tools import mcp

PUBLIC_URL = "https://mcpv1.example.ts.net"


def test_streamable_http_is_stateless() -> None:
    """PAL is a request/response tool server with no server-initiated state.

    Stateless Streamable HTTP means each request is self-contained: clients
    need not carry an Mcp-Session-Id, which is more robust across the varied
    probe/handshake behaviours of MCP connectors.
    """
    assert mcp.settings.stateless_http is True


@pytest.fixture  # type: ignore[misc]
def client(temp_dir: Path) -> TestClient:
    """A TestClient over the full ASGI app with a fixed public URL."""
    settings = Settings(
        prompts_dir=temp_dir / "prompts",
        files_dir=temp_dir / "files",
        oauth_public_url=PUBLIC_URL,
        log_level="DEBUG",
    )
    return TestClient(create_app(settings))


def test_protected_resource_metadata_bare(client: TestClient) -> None:
    """The bare RFC 9728 metadata path is public and advertises the base URL."""
    resp = client.get("/.well-known/oauth-protected-resource")
    assert resp.status_code == 200
    body = resp.json()
    assert body["resource"] == PUBLIC_URL
    assert body["authorization_servers"] == [PUBLIC_URL]


@pytest.mark.parametrize("endpoint", ["sse", "mcp"])  # type: ignore[misc]
def test_protected_resource_metadata_with_path(
    client: TestClient, endpoint: str
) -> None:
    """RFC 9728 inserts the well-known segment before the resource path.

    For resource https://host/sse the client fetches
    /.well-known/oauth-protected-resource/sse — this MUST be public and the
    advertised resource MUST be the canonical endpoint URI including the path.
    """
    resp = client.get(f"/.well-known/oauth-protected-resource/{endpoint}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["resource"] == f"{PUBLIC_URL}/{endpoint}"
    assert body["authorization_servers"] == [PUBLIC_URL]


def test_unauthenticated_sse_challenge_points_to_metadata(client: TestClient) -> None:
    """A 401 on /sse must point the client at its resource metadata (RFC 9728)."""
    resp = client.get("/sse")
    assert resp.status_code == 401
    challenge = resp.headers["www-authenticate"]
    assert challenge.startswith("Bearer")
    assert (
        'resource_metadata="'
        f'{PUBLIC_URL}/.well-known/oauth-protected-resource/sse"' in challenge
    )
