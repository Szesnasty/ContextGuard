"""Property-based invariants over ``guard()`` (step 1.7).

These hold in the phase-1 pass-through and tighten in later phases (e.g. the
conservation invariant relaxes once policy can block chunks). The strategies are
reused by the phase-4 policy fuzzer.
"""

from __future__ import annotations

from contextguard.core import ContextGuard
from contextguard.core.types import Chunk, Outcome, UserContext
from contextguard_eval_harness.strategies import chunk_lists, user_contexts
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

# CI runs more examples; the default profile is fine for local/dev.
_SETTINGS = settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])


@_SETTINGS
@given(user=user_contexts(), chunks=chunk_lists())
def test_accountability_every_chunk_decided_once(user: UserContext, chunks: list[Chunk]) -> None:
    result = ContextGuard().guard(user, "q", chunks)
    decided_ids = [d.chunk_id for d in result.decisions]
    assert sorted(decided_ids) == sorted(c.id for c in chunks)
    assert len(decided_ids) == len(set(decided_ids))


@_SETTINGS
@given(user=user_contexts(), chunks=chunk_lists())
def test_conservation_all_allowed_in_passthrough(user: UserContext, chunks: list[Chunk]) -> None:
    result = ContextGuard().guard(user, "q", chunks)
    assert all(d.outcome == Outcome.ALLOWED for d in result.decisions)


@_SETTINGS
@given(user=user_contexts(), chunks=chunk_lists())
def test_token_monotonicity(user: UserContext, chunks: list[Chunk]) -> None:
    result = ContextGuard().guard(user, "q", chunks)
    assert result.tokens_after <= result.tokens_before


@_SETTINGS
@given(user=user_contexts(), chunks=chunk_lists())
def test_no_duplicate_allowed_ids(user: UserContext, chunks: list[Chunk]) -> None:
    result = ContextGuard().guard(user, "q", chunks)
    ids = [c.id for c in result.allowed_chunks]
    assert len(ids) == len(set(ids))


@_SETTINGS
@given(user=user_contexts(), chunks=chunk_lists())
def test_determinism(user: UserContext, chunks: list[Chunk]) -> None:
    g = ContextGuard()
    assert g.guard(user, "q", chunks) == g.guard(user, "q", chunks)


@_SETTINGS
@given(user=user_contexts(), chunks=chunk_lists())
def test_tenant_not_mutated(user: UserContext, chunks: list[Chunk]) -> None:
    by_id = {c.id: c.tenant for c in chunks}
    result = ContextGuard().guard(user, "q", chunks)
    for c in result.allowed_chunks:
        assert c.tenant == by_id[c.id]


@_SETTINGS
@given(user=user_contexts(), n=st.integers(min_value=0, max_value=0))
def test_empty_edge(user: UserContext, n: int) -> None:
    result = ContextGuard().guard(user, "q", [])
    assert result.allowed_chunks == []
    assert result.tokens_before == 0
