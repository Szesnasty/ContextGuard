"""Prometheus product metrics for the HTTP adapter (Tier A).

The ``cg_*`` product metrics (ADR-003) live here and are exposed via
``GET /metrics`` (the design decision in architecture notes: ``prometheus_client`` +
``/metrics``, no Grafana in the MVP). These are an adapter-tier concern:
``prometheus_client`` is infra, so this module is part of the ``[api]`` tier and
is never imported by ``contextguard.core`` (ADR-010, zero-infra core).

The counters turn the guard's guarantees into numbers an operator can scrape:

* ``cg_chunks_retrieved_total`` / ``cg_chunks_allowed_total`` - throughput and
  the share of context that actually reaches the model.
* ``cg_chunks_blocked_total{reason}`` - proof the policy is doing work, attributed
  to the rule (or budget) that fired.
* ``cg_chunks_redacted_total{type}`` - the minimization signal (PII vs secret).
* ``cg_tokens_before`` / ``cg_tokens_after`` - the **flagship** minimization
  histograms: how much context the firewall removed.
* ``cg_guard_total_latency_ms`` - the guard SLO.
* ``cg_evidence_records_total`` - one audit record per guarded query.
* ``cg_cross_tenant_attempts_blocked_total`` - the tenant-isolation KPI (B3.3).
* ``cg_replay_mismatch_total`` - the determinism alarm: a replay of the same
  input that yields a different decision means a non-deterministic dependency
  crept into core. Healthy value is **0** (ADR-003 / DoD#7).

Deferred (documented engineering decisions, not omissions):

* ``cg_policy_eval_latency_ms`` - measuring the policy step *in isolation* needs a
  timing seam *inside* the core pipeline, which cannot import ``prometheus_client``
  without breaking the zero-infra core (ADR-010). It lands when core grows a
  duration hook the adapter can observe; ``cg_guard_total_latency_ms`` covers the
  end-to-end SLO meanwhile.
* ``cg_sensitive_chunks_detected_total{type}`` - counting PII/secrets across *all*
  retrieved chunks (including blocked ones) needs the enriched view of the whole
  candidate set; :class:`GuardedContext` exposes only the survivors. Rather than
  under-count or duplicate enrichment in the adapter, this lands when the guard
  surfaces enriched candidates. The minimization that was *acted on* is already
  visible via ``cg_chunks_redacted_total`` and ``cg_chunks_blocked_total``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from contextguard_contracts import Outcome
from prometheus_client import Counter, Histogram

if TYPE_CHECKING:
    from contextguard_contracts import GuardedContext

_TOKEN_BUCKETS = (0, 50, 100, 250, 500, 1000, 2000, 4000, 8000, 16000, float("inf"))
_LATENCY_MS_BUCKETS = (0.5, 1, 2.5, 5, 10, 25, 50, 100, 250, 500, 1000, float("inf"))

chunks_retrieved = Counter(
    "cg_chunks_retrieved",
    "Chunks handed to the guard (everything the retriever returned).",
)
chunks_allowed = Counter(
    "cg_chunks_allowed",
    "Chunks the policy allowed through to the model unmodified.",
)
chunks_blocked = Counter(
    "cg_chunks_blocked",
    "Chunks the guard blocked, labelled by the reason that fired.",
    ["reason"],
)
chunks_redacted = Counter(
    "cg_chunks_redacted",
    "Chunks whose sensitive spans were masked before assembly, by span type.",
    ["type"],
)
tokens_before = Histogram(
    "cg_tokens_before",
    "Context tokens retrieved before the firewall (per guarded query).",
    buckets=_TOKEN_BUCKETS,
)
tokens_after = Histogram(
    "cg_tokens_after",
    "Context tokens that actually reached the model (per guarded query).",
    buckets=_TOKEN_BUCKETS,
)
guard_total_latency_ms = Histogram(
    "cg_guard_total_latency_ms",
    "Wall-clock latency of one guard() call (retrieval excluded), in milliseconds.",
    buckets=_LATENCY_MS_BUCKETS,
)
evidence_records = Counter(
    "cg_evidence_records",
    "Evidence records emitted (one per guarded query).",
)
cross_tenant_attempts_blocked = Counter(
    "cg_cross_tenant_attempts_blocked",
    "Chunks blocked because they belonged to a different tenant than the caller.",
    ["tenant"],
)
replay_mismatch = Counter(
    "cg_replay_mismatch",
    "Replays of a stored evidence record that reproduced a different decision.",
)


def record_guard_metrics(guarded: GuardedContext, *, latency_seconds: float) -> None:
    """Emit the per-query ``cg_*`` product metrics from one guard result.

    Called by the HTTP routers after every ``guard()`` call. Reads only the
    public :class:`GuardedContext`, so core stays unaware of metrics (ADR-004).
    """
    chunks_retrieved.inc(len(guarded.decisions))

    by_id = {chunk.id: chunk for chunk in guarded.allowed_chunks}
    for decision in guarded.decisions:
        if decision.outcome is Outcome.ALLOWED:
            chunks_allowed.inc()
        elif decision.outcome is Outcome.BLOCKED:
            reason = decision.reasons[0] if decision.reasons else "unspecified"
            chunks_blocked.labels(reason=reason).inc()
        elif decision.outcome is Outcome.REDACTED:
            chunk = by_id.get(decision.chunk_id)
            if chunk is None:
                continue
            if chunk.secret_spans:
                chunks_redacted.labels(type="secret").inc()
            if chunk.pii_spans:
                chunks_redacted.labels(type="pii").inc()

    tokens_before.observe(guarded.tokens_before)
    tokens_after.observe(guarded.tokens_after)
    guard_total_latency_ms.observe(latency_seconds * 1000.0)
    evidence_records.inc()


def record_replay_mismatch(*, mismatch: bool) -> None:
    """Increment the determinism alarm when a replay reproduced a different decision.

    The healthy value is ``0`` across the golden set (ADR-003 / DoD#7): a non-zero
    count means a non-deterministic dependency reached core.
    """
    if mismatch:
        replay_mismatch.inc()


__all__ = [
    "chunks_allowed",
    "chunks_blocked",
    "chunks_redacted",
    "chunks_retrieved",
    "cross_tenant_attempts_blocked",
    "evidence_records",
    "guard_total_latency_ms",
    "record_guard_metrics",
    "record_replay_mismatch",
    "replay_mismatch",
    "tokens_after",
    "tokens_before",
]
