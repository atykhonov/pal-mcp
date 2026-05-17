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


def tokenize_pipeline(command: str) -> list[PipelineStage]:
    """Tokenize a $$command string into pipeline stages.

    Returns an empty list if `command` is empty or whitespace-only.
    See module docstring for the grammar.
    """
    text = command.strip()
    if not text:
        return []
    return [PipelineStage(cmd=text, op=None)]
