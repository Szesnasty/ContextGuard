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

from functools import lru_cache
from typing import TYPE_CHECKING

from contextguard.core import ContextGuard

if TYPE_CHECKING:
    from contextguard.llm.gateway import LLMGateway
    from contextguard.retrieval.retriever import HybridRetriever


@lru_cache
def get_context_guard() -> ContextGuard:
    """The guard on the request path. Pass-through until phase 4 adds a policy."""
    return ContextGuard()


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


__all__ = ["get_context_guard", "get_llm_gateway", "get_retriever"]
