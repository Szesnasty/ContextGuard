"""Zero-infra decision core (ADR-004, ADR-010).

Pure, deterministic, in-memory. MUST NOT import anything heavier than
``pydantic`` + ``pyyaml``. No DB, no network, no models.

Quickstart (Tier B, zero infra):

    from contextguard.core import ContextGuard
    from contextguard.core.types import Chunk, Classification, UserContext

    guard = ContextGuard()
    user = UserContext(sub="u1", tenant="acme", role="sales", purpose="support")
    chunks = [Chunk(id="c1", doc_id="d1", tenant="acme",
                    text="hello world", classification=Classification.PUBLIC)]
    result = guard.guard(user, "hi", chunks)
    assert result.allowed_chunks  # phase 1: everything is allowed
"""

from __future__ import annotations

from contextguard.core.guard import ContextGuard

__all__ = ["ContextGuard"]
