"""The three-stage pipeline seam (step 1.5, to be filled by ADR-005).

``guard()`` orchestrates an ordered pipeline: ``pre_retrieval`` →
``mid_retrieval`` → ``post_retrieval``. In phase 1 every stage is a no-op; later
phases drop real logic (classification, policy, redaction) into these slots
without changing the ``guard()`` signature. Defining the seam now is cheap;
retrofitting it once logic exists would not be.

``PipelineContext`` is an **internal** working type — not the public contract.
It carries mutable working state and a short-circuit hook so a stage can mark a
chunk decided and later stages skip it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from contextguard.core.types import Chunk, ChunkDecision, UserContext


@dataclass
class PipelineContext:
    """Mutable working state threaded through the stages of one ``guard()`` call."""

    user: UserContext
    query: str
    candidate_chunks: list[Chunk]
    decisions: dict[str, ChunkDecision] = field(default_factory=dict)
    metrics: dict[str, int] = field(default_factory=dict)

    def is_decided(self, chunk_id: str) -> bool:
        """True if some stage already reached a verdict for this chunk."""
        return chunk_id in self.decisions

    def mark_decided(self, decision: ChunkDecision) -> None:
        """Short-circuit hook: record a verdict so later stages skip the chunk."""
        self.decisions[decision.chunk_id] = decision


@runtime_checkable
class Stage(Protocol):
    """A pipeline stage transforms the context and returns it."""

    name: str

    def run(self, ctx: PipelineContext) -> PipelineContext: ...


class _NoOpStage:
    """A stage that returns the context unchanged (phase-1 placeholder)."""

    def __init__(self, name: str) -> None:
        self.name = name

    def run(self, ctx: PipelineContext) -> PipelineContext:
        return ctx


class PreRetrieval(_NoOpStage):
    def __init__(self) -> None:
        super().__init__("pre_retrieval")


class MidRetrieval(_NoOpStage):
    def __init__(self) -> None:
        super().__init__("mid_retrieval")


class PostRetrieval(_NoOpStage):
    def __init__(self) -> None:
        super().__init__("post_retrieval")


class Pipeline:
    """Runs stages in deterministic order."""

    def __init__(self, stages: Sequence[Stage] | None = None) -> None:
        self.stages: list[Stage] = (
            list(stages)
            if stages is not None
            else [
                PreRetrieval(),
                MidRetrieval(),
                PostRetrieval(),
            ]
        )

    def run(self, ctx: PipelineContext) -> PipelineContext:
        for stage in self.stages:
            ctx = stage.run(ctx)
        return ctx


__all__ = [
    "MidRetrieval",
    "Pipeline",
    "PipelineContext",
    "PostRetrieval",
    "PreRetrieval",
    "Stage",
]
