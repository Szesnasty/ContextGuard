"""The ContextGuard entry point — the three lines of defense (ADR-004, ADR-005).

``ContextGuard.guard()`` is the signature the whole product is built around.
Without a policy it is a deliberately permissive pass-through (zero-infra
default). With a policy it runs the three lines of defense in one in-memory
pipeline — **enrich** (PII/secret/injection detection), **policy** (per-chunk
allow/block/redact at mid-retrieval), **redact** (mask the text of redacted
chunks) — then composes the survivors under an optional token budget and emits
one evidence record.

It is the exact object a Tier B drop-in user imports: it runs with nothing but
``local core install`` — no DB, no network, no frameworks (ADR-010).
``from_policy()`` builds a guard from a YAML file with zero infra.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import yaml
from contextguard_policy_dsl import Policy, PolicyEngine

from contextguard.core.enrichment_stage import EnrichmentStage
from contextguard.core.evidence_jsonl import EvidenceSink, JsonlEvidenceSink
from contextguard.core.pipeline import Pipeline, PipelineContext
from contextguard.core.policy_stage import PolicyStage
from contextguard.core.redaction_stage import RedactionStage
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
        token_budget: int | None = None,
        pipeline: Pipeline | None = None,
        sink: EvidenceSink | None = None,
    ) -> None:
        self.policy = policy
        self._counter = counter
        self._token_budget = token_budget
        if pipeline is not None:
            self._pipeline = pipeline
        elif policy is not None:
            # Three lines of defense (ADR-005): enrich → policy → redact.
            self._pipeline = Pipeline(
                [EnrichmentStage(), PolicyStage(PolicyEngine(policy)), RedactionStage()]
            )
        else:
            self._pipeline = Pipeline()
        # Default sink is the zero-infra JSONL/in-memory one (ADR-010). A Tier-A
        # caller can inject a durable sink (e.g. PostgresEvidenceSink) that the
        # core never imports.
        self._sink: EvidenceSink = sink if sink is not None else JsonlEvidenceSink(evidence_path)

    @classmethod
    def from_policy(
        cls,
        path: str | Path,
        *,
        evidence_path: str | Path | None = None,
        token_budget: int | None = None,
        sink: EvidenceSink | None = None,
    ) -> ContextGuard:
        """Build a guard from a YAML policy file — zero infra (ADR-010).

        The policy is parsed, validated, and enforced per chunk at mid-retrieval.
        No DB and no network are touched.
        """
        raw = Path(path).read_text(encoding="utf-8")
        data = yaml.safe_load(raw) or {}
        if not isinstance(data, dict):
            raise ValueError("policy file must contain a YAML mapping")
        return cls(
            policy=Policy.from_dict(data),
            evidence_path=evidence_path,
            token_budget=token_budget,
            sink=sink,
        )

    def guard(
        self,
        user: UserContext,
        query: str,
        candidate_chunks: list[Chunk],
    ) -> GuardedContext:
        """Run the three lines of defense and assemble a guarded context."""
        ctx = PipelineContext(
            user=user,
            query=query,
            candidate_chunks=list(candidate_chunks),
        )
        ctx = self._pipeline.run(ctx)

        decisions: list[ChunkDecision] = []
        allowed: list[Chunk] = []
        # Iterate the post-pipeline chunks: enriched, and redacted where decided.
        for chunk in ctx.candidate_chunks:
            decision = ctx.decisions.get(chunk.id) or ChunkDecision(
                chunk_id=chunk.id,
                outcome=Outcome.ALLOWED,
                reasons=["passthrough"],
            )
            decisions.append(decision)
            # Allowed and redacted chunks both reach the context (redacted text is
            # already masked by RedactionStage). Blocked chunks are dropped.
            if decision.outcome in (Outcome.ALLOWED, Outcome.REDACTED):
                allowed.append(chunk)

        allowed, decisions = self._apply_token_budget(allowed, decisions)

        # tokens_before = everything retrieved (pre-redaction); tokens_after =
        # what actually reaches the model (blocked dropped, redacted masked).
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

    def _apply_token_budget(
        self, allowed: list[Chunk], decisions: list[ChunkDecision]
    ) -> tuple[list[Chunk], list[ChunkDecision]]:
        """Drop lowest-ranked allowed chunks that overflow the token budget.

        The composer assembles chunks in input (rank) order; once the budget is
        exhausted the remaining chunks are dropped and their decision flips to
        ``BLOCKED`` with an attributed reason, so the drop is auditable.
        """
        if self._token_budget is None:
            return allowed, decisions
        kept: list[Chunk] = []
        dropped: set[str] = set()
        used = 0
        for chunk in allowed:
            cost = count_chunk_tokens([chunk.text], counter=self._counter)
            if used + cost > self._token_budget:
                dropped.add(chunk.id)
                continue
            used += cost
            kept.append(chunk)
        if not dropped:
            return allowed, decisions
        rewritten = [
            ChunkDecision(
                chunk_id=d.chunk_id,
                outcome=Outcome.BLOCKED,
                reasons=[*d.reasons, "token-budget-exceeded"],
                policies_triggered=d.policies_triggered,
            )
            if d.chunk_id in dropped
            else d
            for d in decisions
        ]
        return kept, rewritten

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
