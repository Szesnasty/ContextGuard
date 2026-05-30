"""``POST /v1/query`` - the live RAG path (Milestone B1.6).

Wires the full flow behind one endpoint: retrieve -> ``guard()`` -> build a cited
prompt -> call the model. ``guard()`` is already on the path (pass-through today),
so phase 4 flips a switch rather than rebuilding the flow (ADR-005). The HTTP
layer stays a thin adapter (ADR-004): it converts types and handles transport
errors; all decisions live in ``core``.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

import structlog
from contextguard_contracts import (
    Chunk,
    Classification,
    QueryRequest,
    QueryResponse,
    RetrievedChunk,
    UserContext,
)
from fastapi import APIRouter, Depends, HTTPException

from contextguard.api.auth import get_current_user
from contextguard.api.deps import get_context_guard, get_llm_gateway, get_retriever
from contextguard.retrieval.prompt import build_prompt

if TYPE_CHECKING:
    from contextguard.core import ContextGuard
    from contextguard.llm.gateway import LLMGateway

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["query"])


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


def _to_retrieved(hit: Any) -> RetrievedChunk:
    """Adapt a retrieval hit into the public :class:`RetrievedChunk` model."""
    return RetrievedChunk(
        id=hit.id,
        doc_id=hit.doc_id,
        tenant=hit.tenant,
        classification=Classification(str(hit.classification)),
        text=hit.text,
        score=float(hit.score),
        metadata=dict(getattr(hit, "metadata", {}) or {}),
    )


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

    guarded = guard.guard(user, request.query, [_to_chunk(h) for h in hits])
    messages = build_prompt(request.query, guarded.allowed_chunks)

    try:
        completion = gateway.complete(messages)
    except Exception as exc:
        log.error("query.model_failed", error=str(exc))
        raise HTTPException(
            status_code=502,
            detail={"error": "model call failed", "trace_id": trace_id},
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
        retrieved_chunks=[_to_retrieved(h) for h in hits],
        guarded_context=guarded,
    )


__all__ = ["router"]
