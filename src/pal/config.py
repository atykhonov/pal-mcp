"""Configuration using pydantic-settings."""

from __future__ import annotations

import logging
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_prefix="PAL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    transport: Annotated[
        Literal["sse", "stdio"],
        Field(description="Transport type: 'sse' for HTTP/SSE or 'stdio' for standard I/O"),
    ] = "sse"

    server_port: Annotated[int, Field(description="Server port")] = 8090
    server_host: Annotated[str, Field(description="Server host")] = "0.0.0.0"

    ssl_certfile: Annotated[
        Path | None, Field(description="Path to SSL certificate file")
    ] = None
    ssl_keyfile: Annotated[
        Path | None, Field(description="Path to SSL key file")
    ] = None

    instructions_dir: Annotated[
        Path, Field(description="Directory for instruction files")
    ] = Path("~/.mcp-commands")

    files_dir: Annotated[Path, Field(description="Directory for static files")] = Path(
        "~/.mcp-commands/files"
    )

    prompts_dir: Annotated[
        Path | None, Field(description="Directory for custom prompts")
    ] = None

    log_level: Annotated[str, Field(description="Logging level")] = "INFO"

    # OAuth settings
    oauth_enabled: Annotated[
        bool, Field(description="Enable OAuth 2.0 for external connections")
    ] = True

    oauth_public_url: Annotated[
        str | None,
        Field(description="Public URL for OAuth redirects (e.g., https://host.ts.net)"),
    ] = None

    oauth_secret: Annotated[
        str,
        Field(description="Secret key for signing tokens (set PAL_OAUTH_SECRET for persistence)"),
    ] = "pal-default-secret-change-in-production"

    oauth_token_expiry: Annotated[
        int, Field(description="Token expiry in seconds (default 24 hours)")
    ] = 86400

    oauth_allowed_networks: Annotated[
        str,
        Field(description="Comma-separated CIDR ranges that bypass OAuth"),
    ] = "127.0.0.0/8,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,100.64.0.0/10"

    # Meilisearch settings
    meilisearch_url: Annotated[
        str | None,
        Field(description="Meilisearch URL for notes commands (e.g., http://localhost:7700)"),
    ] = None

    # Ollama settings
    ollama_url: Annotated[
        str,
        Field(description="Ollama URL for AI features (e.g., http://localhost:11434)"),
    ] = "http://localhost:11434"

    ollama_model: Annotated[
        str,
        Field(description="Ollama model for AI features (e.g., llama3.2, mistral)"),
    ] = "llama3.2"

    # Notes AI settings
    notes_ai_provider: Annotated[
        Literal["mcp-sampling", "ollama", "pal-follow-up", "none"],
        Field(
            description=(
                "AI provider for notes tag generation: "
                "'mcp-sampling' (uses connected client's LLM via MCP protocol - recommended), "
                "'ollama' (local LLM), "
                "'pal-follow-up' (prompts client LLM to run $$notes tags as follow-up), "
                "or 'none' (keyword extraction only)"
            )
        ),
    ] = "mcp-sampling"

    @property
    def oauth_allowed_cidrs(self) -> list[str]:
        """Get list of CIDR ranges that bypass OAuth."""
        return [cidr.strip() for cidr in self.oauth_allowed_networks.split(",") if cidr.strip()]

    @property
    def instructions_path(self) -> Path:
        """Get expanded instructions directory path."""
        return self.instructions_dir.expanduser()

    @property
    def files_path(self) -> Path:
        """Get expanded files directory path."""
        return self.files_dir.expanduser()

    @property
    def prompts_path(self) -> Path:
        """Get prompts directory path.

        Uses prompts_dir if set, otherwise defaults to project-level prompts directory.
        """
        if self.prompts_dir is not None:
            return self.prompts_dir.expanduser()
        # Default: Use the project-level prompts directory
        return Path(__file__).parent.parent.parent / "prompts"

    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        self.instructions_path.mkdir(parents=True, exist_ok=True)
        self.files_path.mkdir(parents=True, exist_ok=True)
        self.prompts_path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def setup_logging(settings: Settings | None = None) -> logging.Logger:
    """Configure and return the application logger."""
    if settings is None:
        settings = get_settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger = logging.getLogger("pal")
    logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Enable DEBUG logging for notes module (tag generation)
    notes_logger = logging.getLogger("pal.tools.notes")
    notes_logger.setLevel(logging.DEBUG)

    return logger
