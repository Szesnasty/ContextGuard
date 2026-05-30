"""Prometheus product metrics for the HTTP adapter (Tier A).

The product counters live here and are exposed via ``GET /metrics`` (the design
decision in architecture notes: ``prometheus_client`` + ``/metrics``, no Grafana in the
MVP). These are an adapter-tier concern: ``prometheus_client`` is infra, so this
module is part of the ``[api]`` tier and is never imported by
``contextguard.core`` (ADR-010, zero-infra core).

``cg_cross_tenant_attempts_blocked_total`` is the tenant-isolation proof in a
number: every time the scan path blocks a chunk that belonged to a different
tenant than the caller, this counter increments. It is the HTTP-observable form
of the in-memory isolation guarantee proven in A3 (Milestone B3.3).
"""

from __future__ import annotations

from prometheus_client import Counter

cross_tenant_attempts_blocked = Counter(
    "cg_cross_tenant_attempts_blocked",
    "Chunks blocked because they belonged to a different tenant than the caller.",
    ["tenant"],
)

__all__ = ["cross_tenant_attempts_blocked"]
