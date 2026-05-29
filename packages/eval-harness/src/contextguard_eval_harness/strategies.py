"""Reusable Hypothesis strategies for ContextGuard domain types.

Built in phase 1 so the policy engine (phase 4 / Milestone B) inherits a fuzz
harness instead of a blank page. The strategies generate valid ``UserContext``,
``Chunk``, and chunk lists (possibly multi-tenant).
"""

from __future__ import annotations

from contextguard_contracts import Chunk, Classification, UserContext
from hypothesis import strategies as st

_TENANTS = ["acme", "globex", "initech", "umbrella"]
_ROLES = ["sales", "engineer", "admin", "support", "legal"]
_PURPOSES = ["support", "analytics", "audit", "dev"]


def _identifiers() -> st.SearchStrategy[str]:
    return st.text(
        alphabet=st.characters(min_codepoint=97, max_codepoint=122),
        min_size=1,
        max_size=12,
    )


def user_contexts() -> st.SearchStrategy[UserContext]:
    return st.builds(
        UserContext,
        sub=_identifiers(),
        tenant=st.sampled_from(_TENANTS),
        role=st.sampled_from(_ROLES),
        purpose=st.sampled_from(_PURPOSES),
        labels=st.lists(_identifiers(), max_size=4),
    )


def chunks(tenant: str | None = None) -> st.SearchStrategy[Chunk]:
    tenant_strategy = st.just(tenant) if tenant is not None else st.sampled_from(_TENANTS)
    return st.builds(
        Chunk,
        id=st.uuids().map(str),
        doc_id=_identifiers(),
        tenant=tenant_strategy,
        text=st.text(max_size=200),
        classification=st.sampled_from(list(Classification)),
        metadata=st.dictionaries(_identifiers(), _identifiers(), max_size=3),
    )


def chunk_lists(max_size: int = 8) -> st.SearchStrategy[list[Chunk]]:
    """Lists of chunks with unique ids, possibly spanning multiple tenants."""
    return st.lists(chunks(), max_size=max_size, unique_by=lambda c: c.id)


__all__ = ["chunk_lists", "chunks", "user_contexts"]
