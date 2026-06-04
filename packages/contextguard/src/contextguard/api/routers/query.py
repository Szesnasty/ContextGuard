"""``POST /v1/query`` - the live RAG path (Milestone B1.6).

Wires the full flow behind one endpoint: retrieve -> ``guard()`` -> build a cited
prompt -> call the model. ``guard()`` is already on the path (pass-through today),
so phase 4 flips a switch rather than rebuilding the flow (ADR-005). The HTTP
layer stays a thin adapter (ADR-004): it converts types and handles transport
errors; all decisions live in ``core``.
"""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING, Any

import structlog
from contextguard_contracts import (
    Chunk,
    Classification,
    GuardedContext,
    Outcome,
    QueryRequest,
    QueryResponse,
    RetrievedChunk,
    UserContext,
)
from fastapi import APIRouter, Depends, HTTPException

from contextguard.api.auth import get_current_user
from contextguard.api.deps import get_context_guard, get_llm_gateway, get_retriever
from contextguard.api.metrics import record_guard_metrics
from contextguard.retrieval.prompt import build_prompt

if TYPE_CHECKING:
    from contextguard.core import ContextGuard
    from contextguard.llm.gateway import LLMGateway

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["query"])

_WITHHELD_TEXT = "[withheld by ContextGuard: this chunk did not reach the model]"


def _to_chunk(hit: Any) -> Chunk:
    """Adapt a retrieval hit into a domain :class:`Chunk` for the guard."""
    return Chunk(
        id=hit.id,
        doc_id=hit.doc_id,
        tenant=hit.tenant,
        text=hit.text,
        classification=Classification(str(hit.classification)),
        metadata=dict(getattr(hit, "metadata", {}) or {}),
    )


def _to_retrieved(hit: Any, *, text: str | None = None) -> RetrievedChunk:
    """Adapt a retrieval hit into the public :class:`RetrievedChunk` model.

    The public query response is user-facing. It may expose retrieval provenance,
    but it must not leak the raw text of chunks that the guard blocked.
    """
    return RetrievedChunk(
        id=hit.id,
        doc_id=hit.doc_id,
        tenant=hit.tenant,
        classification=Classification(str(hit.classification)),
        text=hit.text if text is None else text,
        score=float(hit.score),
        metadata=dict(getattr(hit, "metadata", {}) or {}),
    )


def _safe_retrieved_chunks(hits: list[Any], guarded: GuardedContext) -> list[RetrievedChunk]:
    """Return retrieved provenance with text constrained by the guard verdict.

    Allowed chunks expose the text that actually reached the model. Redacted
    chunks expose their masked text. Blocked chunks expose identity/provenance
    only, never the original sensitive payload. If a hit somehow has no decision,
    fail closed and withhold its text.
    """
    decisions = {decision.chunk_id: decision for decision in guarded.decisions}
    allowed = {chunk.id: chunk for chunk in guarded.allowed_chunks}
    safe: list[RetrievedChunk] = []
    for hit in hits:
        decision = decisions.get(hit.id)
        guarded_chunk = allowed.get(hit.id)
        if decision is None or decision.outcome is Outcome.BLOCKED or guarded_chunk is None:
            text = _WITHHELD_TEXT
        else:
            text = guarded_chunk.text
        safe.append(_to_retrieved(hit, text=text))
    return safe


@router.post("/v1/query", response_model=QueryResponse)
def query(
    request: QueryRequest,
    user: UserContext = Depends(get_current_user),
    retriever: Any = Depends(get_retriever),
    guard: ContextGuard = Depends(get_context_guard),
    gateway: LLMGateway = Depends(get_llm_gateway),
) -> QueryResponse:
    """Retrieve, guard, build a cited prompt, and return a grounded answer."""
    trace_id = uuid.uuid4().hex
    log = logger.bind(trace_id=trace_id, tenant=user.tenant, sub=user.sub)
    log.info("query.received", k=request.k)

    try:
        hits = retriever.retrieve(request.query, k=request.k)
    except Exception as exc:
        log.error("query.retrieval_failed", error=str(exc))
        raise HTTPException(
            status_code=503,
            detail={"error": "retrieval unavailable", "trace_id": trace_id},
        ) from exc

    started = time.perf_counter()
    guarded = guard.guard(user, request.query, [_to_chunk(h) for h in hits])
    record_guard_metrics(guarded, latency_seconds=time.perf_counter() - started)
    messages = build_prompt(request.query, guarded.allowed_chunks)

    try:
        completion = gateway.complete(messages)
    except Exception as exc:
        log.error("query.model_failed", error=str(exc))
        raise HTTPException(
            status_code=502,
            detail={
                "error": (
                    "model unavailable - check that Ollama is running and "
                    "the selected model is installed"
                ),
                "trace_id": trace_id,
            },
        ) from exc

    log.info(
        "query.answered",
        retrieved=len(hits),
        allowed=len(guarded.allowed_chunks),
        prompt_tokens=completion.prompt_tokens,
        completion_tokens=completion.completion_tokens,
    )
    return QueryResponse(
        answer=completion.text,
        retrieved_chunks=_safe_retrieved_chunks(hits, guarded),
        guarded_context=guarded,
    )


__all__ = ["router"]
