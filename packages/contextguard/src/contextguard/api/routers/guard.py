"""``POST /v1/guard`` - scan-only enforcement (Milestone B3.3).

The decision surface without generation: the verified identity (from the Bearer
token, ADR-015) plus a query and a set of candidate chunks in, a
:class:`GuardedContext` (per-chunk allow/block/redact + reasons) out - **no
prompt is built and no model is called**. This is the endpoint other people's
pipelines, CI gates, and red-team harnesses call to get ContextGuard's verdict
on context they already hold (pattern: a ``/scan`` endpoint).

Because the caller supplies the chunks, the path needs neither retrieval nor a
database: the guard runs in the zero-infra core (ADR-004, ADR-010). Tenant
isolation is the headline guarantee here, so every cross-tenant chunk the policy
blocks is counted into ``cg_cross_tenant_attempts_blocked_total``.
"""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING

import structlog
from contextguard_contracts import GuardedContext, GuardRequest, Outcome, UserContext
from fastapi import APIRouter, Depends

from contextguard.api.auth import get_current_user
from contextguard.api.deps import get_scan_guard
from contextguard.api.metrics import cross_tenant_attempts_blocked, record_guard_metrics

if TYPE_CHECKING:
    from contextguard.core import ContextGuard

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["guard"])


@router.post("/v1/guard", response_model=GuardedContext)
def guard_scan(
    request: GuardRequest,
    user: UserContext = Depends(get_current_user),
    guard: ContextGuard = Depends(get_scan_guard),
) -> GuardedContext:
    """Adjudicate caller-supplied chunks against the policy - no model call."""
    trace_id = uuid.uuid4().hex
    log = logger.bind(trace_id=trace_id, tenant=user.tenant, sub=user.sub)
    log.info("guard.received", candidates=len(request.candidate_chunks))

    started = time.perf_counter()
    guarded = guard.guard(user, request.query, list(request.candidate_chunks))
    record_guard_metrics(guarded, latency_seconds=time.perf_counter() - started)

    blocked_ids = {d.chunk_id for d in guarded.decisions if d.outcome == Outcome.BLOCKED}
    cross_tenant_blocked = sum(
        1
        for chunk in request.candidate_chunks
        if chunk.id in blocked_ids and chunk.tenant != user.tenant
    )
    if cross_tenant_blocked:
        cross_tenant_attempts_blocked.labels(tenant=user.tenant).inc(cross_tenant_blocked)

    log.info(
        "guard.scanned",
        allowed=len(guarded.allowed_chunks),
        blocked=len(blocked_ids),
        cross_tenant_blocked=cross_tenant_blocked,
    )
    return guarded


__all__ = ["router"]
