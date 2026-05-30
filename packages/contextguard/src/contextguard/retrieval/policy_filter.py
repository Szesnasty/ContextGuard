"""Derive a retrieval-time prefilter from a policy (Milestone B3.1, ADR-005).

This is the first line of defense in ADR-005: instead of fetching every chunk
and filtering afterwards, the policy is turned into structural predicates -
tenant + the set of classifications the user is not categorically denied - that
are pushed into the pgvector ``WHERE`` *before* kNN. Unauthorised chunks never
enter the candidate set, so cross-tenant chunks are unreachable by construction.

It is deliberately pure and zero-infra (policy DSL + contracts only): the same
:class:`RetrievalFilter` feeds both the dense SQL query and the in-memory BM25
half, while the authoritative per-chunk ``guard()`` still runs afterwards
(defense in depth). The prefilter is *sound* - it only ever removes chunks the
policy would categorically deny - never a substitute for the guard.
"""

from __future__ import annotations

from dataclasses import dataclass

from contextguard_contracts.models import UserContext
from contextguard_policy_dsl import Policy, PolicyEngine


@dataclass(frozen=True)
class RetrievalFilter:
    """Structural predicates pushed into retrieval before ranking.

    ``tenant`` enforces hard tenant isolation (a user only ever reaches their own
    tenant's chunks). ``allowed_classifications`` is the sound set derived from
    the policy; an empty tuple means the user is denied everything (fail-closed).
    """

    tenant: str
    allowed_classifications: tuple[str, ...]


def build_retrieval_filter(policy: Policy, user: UserContext) -> RetrievalFilter:
    """Derive the :class:`RetrievalFilter` for ``user`` under ``policy``.

    Builds the same user view the mid-retrieval :class:`PolicyStage` sees - the
    user dump with roles expanded - so the predicate the database enforces and
    the decision ``guard()`` makes agree.
    """
    engine = PolicyEngine(policy)
    user_view: dict[str, object] = user.model_dump(mode="json")
    user_view["roles"] = policy.expand_roles(user.role)
    return RetrievalFilter(
        tenant=user.tenant,
        allowed_classifications=tuple(engine.allowed_classifications(user_view)),
    )


__all__ = ["RetrievalFilter", "build_retrieval_filter"]
