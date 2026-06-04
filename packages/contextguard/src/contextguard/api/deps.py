"""FastAPI dependency providers for the query path (Milestone B1.6).

These are the single seam the HTTP layer uses to obtain the retriever, the LLM
gateway, and the guard. Defaults wire the real, live components; tests override
them via ``app.dependency_overrides`` with in-process fakes, so the endpoint
logic is exercised in the zero-infra core tier (ADR-004, ADR-010).

Heavy infra (SQLAlchemy, the embedder) is imported lazily inside the provider so
importing the app - or running ``contextguard[api]`` without ``[pgvector]`` -
never pulls a database driver until a query is actually served.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from contextguard.core import ContextGuard
from contextguard.core.evidence_jsonl import EvidenceSink

if TYPE_CHECKING:
    from contextguard.llm.gateway import LLMGateway
    from contextguard.retrieval.retriever import HybridRetriever

logger = structlog.get_logger(__name__)

_DEFAULT_POLICY_PATH = Path("data/policies/example.yaml")


def _evidence_sink() -> EvidenceSink | None:
    """Optional durable evidence sink for the demo/reference deployment.

    The zero-infra default remains in-memory/JSONL. Setting
    ``EVIDENCE_SINK=postgres`` opts the API adapter into Postgres JSONB evidence
    without making the core import a database.
    """
    if (os.environ.get("EVIDENCE_SINK") or "").lower() != "postgres":
        return None
    try:
        from contextguard.db.evidence import PostgresEvidenceSink, create_evidence_schema
        from contextguard.retrieval.store import get_engine
    except ImportError as exc:
        logger.warning("evidence_sink.unavailable", sink="postgres", error=str(exc))
        return None

    try:
        engine = get_engine()
        create_evidence_schema(engine)
        return PostgresEvidenceSink(engine)
    except Exception as exc:
        logger.warning("evidence_sink.unavailable", sink="postgres", error=str(exc))
        return None


def _policy_guard(*, log_event: str) -> ContextGuard:
    """Build a policy-enforcing guard from ``POLICY_PATH`` (or the repo example).

    With no policy file available it degrades to a pass-through guard and logs a
    warning - a guard with no policy is useless but not dangerous (fail-open is
    explicit and observable, never silent).
    """
    raw = os.environ.get("POLICY_PATH")
    path = Path(raw) if raw else _DEFAULT_POLICY_PATH
    sink = _evidence_sink()
    if not path.is_file():
        logger.warning(log_event, path=str(path))
        return ContextGuard(sink=sink)
    return ContextGuard.from_policy(path, sink=sink)


@lru_cache
def get_context_guard() -> ContextGuard:
    """The guard on the ``/v1/query`` request path (phase 4 enforcement).

    Enforces the policy so the answer is grounded **only** in chunks that survive
    the firewall - blocked chunks never reach ``build_prompt`` and so can't leak
    into the model's reply. Built once and cached.
    """
    return _policy_guard(log_event="context_guard.no_policy")


@lru_cache
def get_scan_guard() -> ContextGuard:
    """The policy-enforcing guard behind ``/v1/guard`` (scan-only, B3.3).

    Loads the policy from ``POLICY_PATH``; if unset, falls back to the repo's
    example policy when present. Built once and cached.
    """
    return _policy_guard(log_event="scan_guard.no_policy")


@lru_cache
def get_llm_gateway() -> LLMGateway:
    """The configured LLM gateway (Ollama by default, ADR-014)."""
    from contextguard.llm.gateway import get_gateway

    return get_gateway()


@lru_cache
def get_retriever() -> HybridRetriever:
    """The live hybrid retriever over the seeded pgvector store."""
    from contextguard.retrieval.bootstrap import build_retriever

    return build_retriever()


__all__ = [
    "get_context_guard",
    "get_llm_gateway",
    "get_retriever",
    "get_scan_guard",
]
