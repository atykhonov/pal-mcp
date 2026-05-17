"""Tests for pipeline tokenization."""

from __future__ import annotations

from pal.tools.pipeline import PipelineStage, tokenize_pipeline


class TestTokenizeSingleStage:
    """No pipeline operators present — one stage, no operator."""

    def test_simple_command(self) -> None:
        stages = tokenize_pipeline("echo hello")
        assert stages == [PipelineStage(cmd="echo hello", op=None)]

    def test_empty_string(self) -> None:
        assert tokenize_pipeline("") == []

    def test_whitespace_only(self) -> None:
        assert tokenize_pipeline("   ") == []

    def test_outer_whitespace_stripped(self) -> None:
        stages = tokenize_pipeline("  echo hello  ")
        assert stages == [PipelineStage(cmd="echo hello", op=None)]
