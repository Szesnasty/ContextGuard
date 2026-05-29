"""Pipeline three-stage seam tests (step 1.5)."""

from __future__ import annotations

from contextguard.core import ContextGuard
from contextguard.core.pipeline import (
    MidRetrieval,
    Pipeline,
    PipelineContext,
    PostRetrieval,
    PreRetrieval,
    Stage,
)
from contextguard.core.types import Chunk, ChunkDecision, Classification, Outcome, UserContext


def _user() -> UserContext:
    return UserContext(sub="u1", tenant="acme", role="sales", purpose="support")


def _chunks(n: int) -> list[Chunk]:
    return [
        Chunk(
            id=f"c{i}",
            doc_id="d1",
            tenant="acme",
            text=f"chunk {i}",
            classification=Classification.PUBLIC,
        )
        for i in range(n)
    ]


def _ctx() -> PipelineContext:
    return PipelineContext(user=_user(), query="hi", candidate_chunks=_chunks(2))


class _SpyStage:
    name = "spy"

    def __init__(self, log: list[str], label: str) -> None:
        self._log = log
        self._label = label

    def run(self, ctx: PipelineContext) -> PipelineContext:
        self._log.append(self._label)
        return ctx


def test_default_stage_order() -> None:
    p = Pipeline()
    assert [s.name for s in p.stages] == ["pre_retrieval", "mid_retrieval", "post_retrieval"]


def test_pipeline_runs_in_order() -> None:
    log: list[str] = []
    p = Pipeline([_SpyStage(log, "pre"), _SpyStage(log, "mid"), _SpyStage(log, "post")])
    p.run(_ctx())
    assert log == ["pre", "mid", "post"]


def test_noop_stages_preserve_context() -> None:
    ctx = _ctx()
    out = Pipeline([PreRetrieval(), MidRetrieval(), PostRetrieval()]).run(ctx)
    assert out.candidate_chunks == ctx.candidate_chunks
    assert out.decisions == {}


def test_custom_stage_protocol_plugs_in() -> None:
    log: list[str] = []
    stage: Stage = _SpyStage(log, "custom")
    Pipeline([stage]).run(_ctx())
    assert log == ["custom"]


def test_short_circuit_hook_present() -> None:
    ctx = _ctx()
    assert not ctx.is_decided("c0")
    ctx.mark_decided(ChunkDecision(chunk_id="c0", outcome=Outcome.BLOCKED))
    assert ctx.is_decided("c0")
    assert ctx.decisions["c0"].outcome == Outcome.BLOCKED


def test_guard_still_passthrough_after_pipeline() -> None:
    chunks = _chunks(3)
    result = ContextGuard().guard(_user(), "hi", chunks)
    assert len(result.allowed_chunks) == 3
    assert all(d.outcome == Outcome.ALLOWED for d in result.decisions)


def test_stage_can_decide_and_guard_respects_it() -> None:
    """A stage marking a chunk blocked is honored by guard() (future-proofing)."""

    class BlockFirst:
        name = "block_first"

        def run(self, ctx: PipelineContext) -> PipelineContext:
            if ctx.candidate_chunks:
                ctx.mark_decided(
                    ChunkDecision(chunk_id=ctx.candidate_chunks[0].id, outcome=Outcome.BLOCKED)
                )
            return ctx

    chunks = _chunks(3)
    guard = ContextGuard(pipeline=Pipeline([BlockFirst()]))
    result = guard.guard(_user(), "hi", chunks)
    assert len(result.allowed_chunks) == 2
    assert result.decisions[0].outcome == Outcome.BLOCKED
