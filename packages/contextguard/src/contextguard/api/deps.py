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

if TYPE_CHECKING:
    from contextguard.llm.gateway import LLMGateway
    from contextguard.retrieval.retriever import HybridRetriever

logger = structlog.get_logger(__name__)

_DEFAULT_POLICY_PATH = Path("data/policies/example.yaml")


@lru_cache
def get_context_guard() -> ContextGuard:
    """The guard on the request path. Pass-through until phase 4 adds a policy."""
    return ContextGuard()


@lru_cache
def get_scan_guard() -> ContextGuard:
    """The policy-enforcing guard behind ``/v1/guard`` (scan-only, B3.3).

    Loads the policy from ``POLICY_PATH``; if unset, falls back to the repo's
    example policy when present. With no policy available it degrades to a
    pass-through guard and logs a warning - a scan with no policy is useless but
    not dangerous. Built once and cached.
    """
    raw = os.environ.get("POLICY_PATH")
    path = Path(raw) if raw else _DEFAULT_POLICY_PATH
    if not path.is_file():
        logger.warning("scan_guard.no_policy", path=str(path))
        return ContextGuard()
    return ContextGuard.from_policy(path)


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
