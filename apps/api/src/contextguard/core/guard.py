"""The ContextGuard entry point — phase-1 pass-through (ADR-004, ADR-010).

``ContextGuard.guard()`` is the signature the whole product is built around. In
phase 1 it is a **deliberately insecure pass-through**: it allows every chunk,
counts tokens, and emits one ``allowed`` decision per chunk. This freezes the
end-to-end shape before any logic exists, so phases 3-5 are edits, not rewrites.

It is also the exact object a Tier B drop-in user imports: it runs with nothing
but ``local core install`` — no DB, no network, no frameworks (ADR-010).
``from_policy()`` builds a guard from a YAML file with zero infra; in phase 1 the
policy is loaded but not yet enforced (the DSL lands in Milestone A3).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

from contextguard.core.evidence_jsonl import JsonlEvidenceSink
from contextguard.core.pipeline import Pipeline, PipelineContext
from contextguard.core.tokens import TokenCounter, count_chunk_tokens
from contextguard.core.types import (
    Chunk,
    ChunkDecision,
    EvidenceMetrics,
    EvidenceRecord,
    GuardedContext,
    Outcome,
    UserContext,
)


class ContextGuard:
    """Policy-aware context firewall. Phase 1: pass-through, zero-infra."""

    def __init__(
        self,
        *,
        policy: dict[str, Any] | None = None,
        evidence_path: str | Path | None = None,
        counter: TokenCounter | None = None,
        pipeline: Pipeline | None = None,
    ) -> None:
        self.policy = policy
        self._counter = counter
        self._pipeline = pipeline or Pipeline()
        self._sink = JsonlEvidenceSink(evidence_path)

    @classmethod
    def from_policy(
        cls,
        path: str | Path,
        *,
        evidence_path: str | Path | None = None,
    ) -> ContextGuard:
        """Build a guard from a YAML policy file — zero infra (ADR-010).

        The policy is parsed and attached now; enforcement arrives in Milestone
        A3. No DB and no network are touched.
        """
        raw = Path(path).read_text(encoding="utf-8")
        policy = yaml.safe_load(raw) or {}
        if not isinstance(policy, dict):
            raise ValueError("policy file must contain a YAML mapping")
        return cls(policy=policy, evidence_path=evidence_path)

    def guard(
        self,
        user: UserContext,
        query: str,
        candidate_chunks: list[Chunk],
    ) -> GuardedContext:
        """Return a guarded context. Phase 1: allow everything, count tokens."""
        ctx = PipelineContext(
            user=user,
            query=query,
            candidate_chunks=list(candidate_chunks),
        )
        ctx = self._pipeline.run(ctx)

        decisions: list[ChunkDecision] = []
        allowed: list[Chunk] = []
        for chunk in candidate_chunks:
            decision = ctx.decisions.get(chunk.id) or ChunkDecision(
                chunk_id=chunk.id,
                outcome=Outcome.ALLOWED,
                reasons=["phase1-passthrough"],
            )
            decisions.append(decision)
            if decision.outcome == Outcome.ALLOWED:
                allowed.append(chunk)

        tokens_before = count_chunk_tokens(
            [c.text for c in candidate_chunks], counter=self._counter
        )
        tokens_after = count_chunk_tokens([c.text for c in allowed], counter=self._counter)

        result = GuardedContext(
            allowed_chunks=allowed,
            decisions=decisions,
            tokens_before=tokens_before,
            tokens_after=tokens_after,
        )
        self._emit_evidence(user, query, result)
        return result

    def last_evidence(self) -> dict[str, object] | None:
        """Return the most recent evidence record as a plain dict (ADR-010)."""
        return self._sink.last_evidence()

    def _emit_evidence(self, user: UserContext, query: str, result: GuardedContext) -> None:
        metrics = EvidenceMetrics(
            chunks_retrieved=len(result.decisions),
            chunks_allowed=sum(1 for d in result.decisions if d.outcome == Outcome.ALLOWED),
            chunks_blocked=sum(1 for d in result.decisions if d.outcome == Outcome.BLOCKED),
            chunks_redacted=sum(1 for d in result.decisions if d.outcome == Outcome.REDACTED),
            tokens_before=result.tokens_before,
            tokens_after=result.tokens_after,
        )
        record = EvidenceRecord(
            query_id=str(uuid4()),
            user=user,
            query=query,
            decisions=result.decisions,
            metrics=metrics,
            policies_triggered=[],
            created_at=datetime.now(UTC),
        )
        self._sink.emit(record)


__all__ = ["ContextGuard"]
