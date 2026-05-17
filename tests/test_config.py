"""Tests for PAL settings."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pal.config import Settings


def test_protocol_header_location_default_is_instructions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default location ships the protocol via FastMCP `instructions`."""
    monkeypatch.delenv("PAL_PROTOCOL_HEADER_LOCATION", raising=False)
    assert Settings().protocol_header_location == "instructions"


@pytest.mark.parametrize("value", ["instructions", "per-call", "both"])
def test_protocol_header_location_accepts_all_modes(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    """All three documented values round-trip via the env var."""
    monkeypatch.setenv("PAL_PROTOCOL_HEADER_LOCATION", value)
    assert Settings().protocol_header_location == value


def test_protocol_header_location_rejects_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pydantic validates the Literal — typos fail at startup, not silently."""
    monkeypatch.setenv("PAL_PROTOCOL_HEADER_LOCATION", "per_call")  # typo (underscore)
    with pytest.raises(ValidationError):
        Settings()


def test_protocol_header_location_settable_via_kwarg(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The field can be overridden at construction time (used by test fixtures)."""
    monkeypatch.delenv("PAL_PROTOCOL_HEADER_LOCATION", raising=False)
    assert Settings(protocol_header_location="per-call").protocol_header_location == "per-call"
