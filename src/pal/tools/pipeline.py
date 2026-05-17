"""Pipeline tokenization for $$commands.

Owns the single source of truth for PAL's pipeline grammar:
left-to-right scan; ` -- ` (space-dash-dash-space) starts raw mode and
halts further tokenization; the operators ` | `, ` && `, and ` ; ` are
recognised only when space-surrounded. There are no escape sequences
and no quoting — anything that needs to contain operator-shaped bytes
goes after a ` -- ` edge marker.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PipelineStage:
    """One stage of a pipeline.

    `cmd` is the stage text with no surrounding whitespace.
    `op` is the operator joining this stage to the *next* stage, or
    None for the final stage (or for a single-stage command).
    """

    cmd: str
    op: str | None


_OPERATORS: tuple[str, ...] = (" && ", " | ", " ; ")
# Order matters: ` && ` must be checked before ` & ` would be (we don't
# recognise ` & ` today; this just documents the lookup-order intent if
# more operators are added).

_RAW_EDGE_MARKER = " -- "


def tokenize_pipeline(command: str) -> list[PipelineStage]:
    """Tokenize a $$command string into pipeline stages.

    Returns an empty list if `command` is empty or whitespace-only.
    See module docstring for the grammar.
    """
    text = command.strip()
    if not text:
        return []

    raw_boundary = text.find(_RAW_EDGE_MARKER)
    scan_limit = raw_boundary if raw_boundary != -1 else len(text)

    stages: list[PipelineStage] = []
    cursor = 0
    while cursor < len(text):
        next_op_index = -1
        next_op: str | None = None
        for op in _OPERATORS:
            idx = text.find(op, cursor)
            if idx == -1 or idx >= scan_limit:
                continue
            if next_op_index == -1 or idx < next_op_index:
                next_op_index = idx
                next_op = op
        if next_op is None:
            stages.append(PipelineStage(cmd=text[cursor:].strip(), op=None))
            break
        stage_text = text[cursor:next_op_index].strip()
        stages.append(PipelineStage(cmd=stage_text, op=next_op.strip()))
        cursor = next_op_index + len(next_op)
    return stages
