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


class TestRawModeEdgeMarker:
    """` -- ` (space-dash-dash-space) starts raw mode for the remainder."""

    def test_double_dash_suppresses_pipe(self) -> None:
        stages = tokenize_pipeline("tr -- hello | world")
        assert stages == [PipelineStage(cmd="tr -- hello | world", op=None)]

    def test_double_dash_suppresses_all_operators(self) -> None:
        stages = tokenize_pipeline("cmd -- a | b && c ; d")
        assert stages == [PipelineStage(cmd="cmd -- a | b && c ; d", op=None)]

    def test_second_double_dash_is_payload(self) -> None:
        stages = tokenize_pipeline("cmd -- foo -- bar | baz")
        assert stages == [PipelineStage(cmd="cmd -- foo -- bar | baz", op=None)]

    def test_operator_before_double_dash_still_splits(self) -> None:
        stages = tokenize_pipeline("a | tr -- hello | world")
        assert stages == [
            PipelineStage(cmd="a", op="|"),
            PipelineStage(cmd="tr -- hello | world", op=None),
        ]

    def test_double_dash_without_spaces_is_not_edge_marker(self) -> None:
        # `--help` is a flag, not a raw-mode marker (no leading space).
        stages = tokenize_pipeline("echo --help")
        assert stages == [PipelineStage(cmd="echo --help", op=None)]

    def test_unicode_payload_passes_through(self) -> None:
        stages = tokenize_pipeline("tr -- 你好 | мир 🌍")
        assert stages == [PipelineStage(cmd="tr -- 你好 | мир 🌍", op=None)]
