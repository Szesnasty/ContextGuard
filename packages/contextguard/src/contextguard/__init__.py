"""ContextGuard — policy-aware context firewall for production RAG.

The zero-infra decision core lives in `contextguard.core` and must not import
anything heavier than pydantic+pyyaml (ADR-004, ADR-010); heavier adapters
(`contextguard.api`, db, llm, …) are gated behind optional extras and loaded
lazily.

The public entry point is re-exported here so `from contextguard import
ContextGuard` works on a bare `local core install` (ADR-013). This import
is zero-infra: it pulls only the core, never a framework.
"""

from __future__ import annotations

from contextguard.core import ContextGuard

__version__ = "0.0.0"

__all__ = ["ContextGuard", "__version__"]
