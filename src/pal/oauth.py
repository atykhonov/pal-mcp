"""OAuth 2.1 implementation for MCP server."""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import secrets
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass, field
from typing import Any

from pal.config import Settings


@dataclass
class Client:
    """Registered OAuth client."""

    client_id: str
    client_name: str
    redirect_uris: list[str]
    created_at: float = field(default_factory=time.time)


@dataclass
class AuthorizationCode:
    """OAuth authorization code."""

    code: str
    client_id: str
    redirect_uri: str
    code_challenge: str
    code_challenge_method: str
    created_at: float = field(default_factory=time.time)
    expires_in: int = 600  # 10 minutes


@dataclass
class AccessToken:
    """OAuth access token."""

    token: str
    client_id: str
    created_at: float = field(default_factory=time.time)
    expires_in: int = 86400  # 24 hours


class OAuthManager:
    """Manages OAuth 2.1 flows for MCP server."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._clients: dict[str, Client] = {}
        self._auth_codes: dict[str, AuthorizationCode] = {}
        self._tokens: dict[str, AccessToken] = {}

    def get_metadata(self) -> dict[str, Any]:
        """Get OAuth authorization server metadata."""
        base_url = self.settings.oauth_public_url or f"http://localhost:{self.settings.server_port}"
        return {
            "issuer": base_url,
            "authorization_endpoint": f"{base_url}/authorize",
            "token_endpoint": f"{base_url}/token",
            "registration_endpoint": f"{base_url}/register",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
            "token_endpoint_auth_methods_supported": ["none"],
            "code_challenge_methods_supported": ["S256"],
            "scopes_supported": ["mcp"],
        }

    def register_client(
        self,
        client_name: str,
        redirect_uris: list[str],
    ) -> Client:
        """Register a new OAuth client (RFC 7591)."""
        client_id = secrets.token_urlsafe(16)
        client = Client(
            client_id=client_id,
            client_name=client_name,
            redirect_uris=redirect_uris,
        )
        self._clients[client_id] = client
        print(f"[OAUTH] Registered client: {client_name} ({client_id})")
        return client

    def get_client(self, client_id: str) -> Client | None:
        """Get a registered client by ID."""
        return self._clients.get(client_id)

    def validate_redirect_uri(self, client_id: str, redirect_uri: str) -> bool:
        """Validate redirect URI for a client."""
        client = self.get_client(client_id)
        if not client:
            return False
        # Allow localhost redirects always (for CLI tools)
        if redirect_uri.startswith("http://localhost") or redirect_uri.startswith("http://127.0.0.1"):
            return True
        return redirect_uri in client.redirect_uris

    def create_authorization_code(
        self,
        client_id: str,
        redirect_uri: str,
        code_challenge: str,
        code_challenge_method: str = "S256",
    ) -> str:
        """Create an authorization code."""
        code = secrets.token_urlsafe(32)
        auth_code = AuthorizationCode(
            code=code,
            client_id=client_id,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
        )
        self._auth_codes[code] = auth_code
        print(f"[OAUTH] Created auth code for client: {client_id}")
        return code

    def exchange_code(
        self,
        code: str,
        client_id: str,
        redirect_uri: str,
        code_verifier: str,
    ) -> AccessToken | None:
        """Exchange authorization code for access token."""
        auth_code = self._auth_codes.get(code)
        if not auth_code:
            print("[OAUTH] Code exchange failed: invalid code")
            return None

        # Check expiration
        if time.time() > auth_code.created_at + auth_code.expires_in:
            del self._auth_codes[code]
            print("[OAUTH] Code exchange failed: code expired")
            return None

        # Validate client_id
        if auth_code.client_id != client_id:
            print("[OAUTH] Code exchange failed: client_id mismatch")
            return None

        # Validate redirect_uri
        if auth_code.redirect_uri != redirect_uri:
            print("[OAUTH] Code exchange failed: redirect_uri mismatch")
            return None

        # Validate PKCE
        if not self._verify_pkce(code_verifier, auth_code.code_challenge, auth_code.code_challenge_method):
            print("[OAUTH] Code exchange failed: PKCE verification failed")
            return None

        # Remove used code
        del self._auth_codes[code]

        # Create access token
        token = self._generate_token(client_id)
        access_token = AccessToken(
            token=token,
            client_id=client_id,
            expires_in=self.settings.oauth_token_expiry,
        )
        self._tokens[token] = access_token
        print(f"[OAUTH] Issued access token for client: {client_id}")
        return access_token

    def validate_token(self, token: str) -> bool:
        """Validate an access token."""
        access_token = self._tokens.get(token)
        if not access_token:
            return False

        # Check expiration
        if time.time() > access_token.created_at + access_token.expires_in:
            del self._tokens[token]
            return False

        return True

    def is_ip_allowed(self, client_ip: str) -> bool:
        """Check if client IP is in allowed networks (bypasses OAuth)."""
        if not self.settings.oauth_enabled:
            return True

        try:
            ip = ipaddress.ip_address(client_ip)
            for cidr in self.settings.oauth_allowed_cidrs:
                try:
                    network = ipaddress.ip_network(cidr)
                    if ip in network:
                        return True
                except ValueError:
                    continue
        except ValueError:
            pass

        return False

    def _verify_pkce(
        self,
        code_verifier: str,
        code_challenge: str,
        code_challenge_method: str,
    ) -> bool:
        """Verify PKCE code challenge."""
        if code_challenge_method != "S256":
            return False

        # S256: BASE64URL(SHA256(code_verifier))
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        computed_challenge = urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        return hmac.compare_digest(computed_challenge, code_challenge)

    def _generate_token(self, client_id: str) -> str:
        """Generate a signed access token."""
        payload = {
            "client_id": client_id,
            "iat": int(time.time()),
            "exp": int(time.time()) + self.settings.oauth_token_expiry,
        }
        payload_bytes = json.dumps(payload).encode()
        payload_b64 = urlsafe_b64encode(payload_bytes).decode()

        signature = hmac.new(
            self.settings.oauth_secret.encode(),
            payload_bytes,
            hashlib.sha256,
        ).digest()
        signature_b64 = urlsafe_b64encode(signature).decode()

        return f"{payload_b64}.{signature_b64}"


# Global OAuth manager instance
_oauth_manager: OAuthManager | None = None


def get_oauth_manager(settings: Settings | None = None) -> OAuthManager:
    """Get or create the OAuth manager instance."""
    global _oauth_manager
    if _oauth_manager is None:
        if settings is None:
            from pal.config import get_settings
            settings = get_settings()
        _oauth_manager = OAuthManager(settings)
    return _oauth_manager
