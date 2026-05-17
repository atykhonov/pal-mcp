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


class TestTokenizeOperators:
    """Each operator splits the command at the operator location."""

    def test_pipe(self) -> None:
        stages = tokenize_pipeline("echo hello | tr")
        assert stages == [
            PipelineStage(cmd="echo hello", op="|"),
            PipelineStage(cmd="tr", op=None),
        ]

    def test_and(self) -> None:
        stages = tokenize_pipeline("foo && bar")
        assert stages == [
            PipelineStage(cmd="foo", op="&&"),
            PipelineStage(cmd="bar", op=None),
        ]

    def test_seq(self) -> None:
        stages = tokenize_pipeline("foo ; bar")
        assert stages == [
            PipelineStage(cmd="foo", op=";"),
            PipelineStage(cmd="bar", op=None),
        ]

    def test_three_stage_pipe(self) -> None:
        stages = tokenize_pipeline("a | b | c")
        assert stages == [
            PipelineStage(cmd="a", op="|"),
            PipelineStage(cmd="b", op="|"),
            PipelineStage(cmd="c", op=None),
        ]

    def test_mixed_operators(self) -> None:
        stages = tokenize_pipeline("a && b ; c")
        assert stages == [
            PipelineStage(cmd="a", op="&&"),
            PipelineStage(cmd="b", op=";"),
            PipelineStage(cmd="c", op=None),
        ]
