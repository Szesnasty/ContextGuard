"""Mid-retrieval policy enforcement stage (ADR-005, line 2).

This stage bridges the zero-infra core to the policy DSL: for each candidate
chunk it asks the :class:`PolicyEngine` whether the chunk may reach this user,
and records an ``allow``/``block``/``redact`` decision with its reason. The
engine sees a plain mapping (``user`` + ``chunk`` dumps, with expanded roles),
keeping the DSL decoupled from the domain models.

Fail-closed (ADR-005 rule #2): a ``deny`` here removes the chunk from the
allowed set; the short-circuit hook means a later stage cannot silently revive
it.
"""

from __future__ import annotations

from contextguard_policy_dsl import Effect, PolicyEngine

from contextguard.core.pipeline import PipelineContext
from contextguard.core.types import ChunkDecision, Outcome

_EFFECT_TO_OUTCOME: dict[Effect, Outcome] = {
    Effect.ALLOW: Outcome.ALLOWED,
    Effect.DENY: Outcome.BLOCKED,
    Effect.REDACT: Outcome.REDACTED,
}


class PolicyStage:
    """Evaluates the policy per chunk and records decisions (mid-retrieval)."""

    name = "mid_retrieval"

    def __init__(self, engine: PolicyEngine) -> None:
        self._engine = engine

    def run(self, ctx: PipelineContext) -> PipelineContext:
        user_view = ctx.user.model_dump(mode="json")
        user_view["roles"] = self._engine.policy.expand_roles(ctx.user.role)
        for chunk in ctx.candidate_chunks:
            if ctx.is_decided(chunk.id):
                continue
            decision = self._engine.evaluate(
                {"user": user_view, "chunk": chunk.model_dump(mode="json")}
            )
            ctx.mark_decided(
                ChunkDecision(
                    chunk_id=chunk.id,
                    outcome=_EFFECT_TO_OUTCOME[decision.effect],
                    reasons=decision.reasons,
                    policies_triggered=(
                        [decision.matched_rule_id] if decision.matched_rule_id else []
                    ),
                )
            )
        return ctx


__all__ = ["PolicyStage"]
