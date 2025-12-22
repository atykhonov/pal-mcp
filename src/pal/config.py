"""Configuration using pydantic-settings."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Annotated

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

    server_port: Annotated[int, Field(description="Server port")] = 8090
    server_host: Annotated[str, Field(description="Server host")] = "0.0.0.0"

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

    return logger
