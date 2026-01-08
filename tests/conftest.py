"""Pytest configuration and fixtures."""

from __future__ import annotations

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from pal.config import Settings, get_settings


@pytest.fixture  # type: ignore[misc]
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture  # type: ignore[misc]
def test_settings(temp_dir: Path) -> Settings:
    """Create test settings with temporary directories."""
    return Settings(
        prompts_dir=temp_dir / "prompts",
        files_dir=temp_dir / "files",
        log_level="DEBUG",
    )


@pytest.fixture(autouse=True)  # type: ignore[misc]
def clear_settings_cache() -> Generator[None, None, None]:
    """Clear the settings cache before and after each test."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
