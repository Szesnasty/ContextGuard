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
from uuid import uuid4

import yaml
from contextguard_policy_dsl import Policy, PolicyEngine

from contextguard.core.evidence_jsonl import JsonlEvidenceSink
from contextguard.core.pipeline import Pipeline, PipelineContext, PostRetrieval, PreRetrieval
from contextguard.core.policy_stage import PolicyStage
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
    """Policy-aware context firewall. Without a policy: pass-through, zero-infra."""

    def __init__(
        self,
        *,
        policy: Policy | None = None,
        evidence_path: str | Path | None = None,
        counter: TokenCounter | None = None,
        pipeline: Pipeline | None = None,
    ) -> None:
        self.policy = policy
        self._counter = counter
        if pipeline is not None:
            self._pipeline = pipeline
        elif policy is not None:
            # Mid-retrieval policy enforcement between the pre/post no-op seams.
            self._pipeline = Pipeline(
                [PreRetrieval(), PolicyStage(PolicyEngine(policy)), PostRetrieval()]
            )
        else:
            self._pipeline = Pipeline()
        self._sink = JsonlEvidenceSink(evidence_path)

    @classmethod
    def from_policy(
        cls,
        path: str | Path,
        *,
        evidence_path: str | Path | None = None,
    ) -> ContextGuard:
        """Build a guard from a YAML policy file — zero infra (ADR-010).

        The policy is parsed, validated, and enforced per chunk at mid-retrieval.
        No DB and no network are touched.
        """
        raw = Path(path).read_text(encoding="utf-8")
        data = yaml.safe_load(raw) or {}
        if not isinstance(data, dict):
            raise ValueError("policy file must contain a YAML mapping")
        return cls(policy=Policy.from_dict(data), evidence_path=evidence_path)

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
            # Allowed and redacted chunks both reach the context; redaction of
            # text content is applied later (phase 5). Blocked chunks are dropped.
            if decision.outcome in (Outcome.ALLOWED, Outcome.REDACTED):
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
        # Unique rule ids that fired, in first-seen order.
        triggered: list[str] = []
        for decision in result.decisions:
            for rule_id in decision.policies_triggered:
                if rule_id not in triggered:
                    triggered.append(rule_id)
        record = EvidenceRecord(
            query_id=str(uuid4()),
            user=user,
            query=query,
            decisions=result.decisions,
            metrics=metrics,
            policies_triggered=triggered,
            created_at=datetime.now(UTC),
        )
        self._sink.emit(record)


__all__ = ["ContextGuard"]
