"""The ContextGuard policy DSL — declarative, framework-agnostic schema.

A policy is plain data (YAML/JSON) validated into these Pydantic models. The
engine ([engine.PolicyEngine][]) evaluates it against a context mapping with no
I/O, so an OPA backend could replace the evaluator later without touching
callers (ADR-003). The DSL is intentionally small and safe: there is no code
execution, only a closed set of operators over named fields.

Decision model (mid-retrieval, ADR-005): each rule has an ``effect``
(``allow``/``deny``/``redact``) and a list of ``when`` conditions joined by AND.
Rules are evaluated by descending ``priority`` (ties keep declaration order);
the first fully-matching rule wins. If none match, ``default_effect`` applies.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

# Sensitivity ordering for ordered comparisons (mirrors contracts.Classification
# without importing it — the DSL stays decoupled from the domain models).
CLASSIFICATION_ORDER: dict[str, int] = {
    "public": 0,
    "internal": 1,
    "confidential": 2,
    "restricted": 3,
}

_STRICT = ConfigDict(extra="forbid")


class Effect(StrEnum):
    """What a matching rule does to a chunk."""

    ALLOW = "allow"
    DENY = "deny"
    REDACT = "redact"


class Operator(StrEnum):
    """The closed set of comparison operators a condition may use."""

    EQ = "eq"
    NEQ = "neq"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"


_ORDERED = {Operator.GT, Operator.GTE, Operator.LT, Operator.LTE}
_REF_ALLOWED = {Operator.EQ, Operator.NEQ}


def _is_orderable(value: Any) -> bool:
    """Ordered operators accept a plain number or a classification literal."""
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    return isinstance(value, str) and value in CLASSIFICATION_ORDER


class Condition(BaseModel):
    """One comparison over a named field of the evaluation context.

    ``field`` is a dotted path such as ``user.role`` or ``chunk.classification``.
    Compare against a literal ``value`` or, for ``eq``/``neq``, another field via
    ``ref`` (e.g. ``chunk.tenant neq user.tenant`` for tenant isolation).
    """

    model_config = _STRICT

    field: str
    op: Operator
    value: Any | None = None
    ref: str | None = None

    @model_validator(mode="after")
    def _validate(self) -> Condition:
        if self.ref is not None:
            if self.value is not None:
                raise ValueError("condition cannot set both 'value' and 'ref'")
            if self.op not in _REF_ALLOWED:
                raise ValueError("'ref' is only valid with 'eq' or 'neq'")
        elif self.value is None:
            raise ValueError("condition must set either 'value' or 'ref'")

        if self.op in _ORDERED and not _is_orderable(self.value):
            raise ValueError(
                f"ordered operator '{self.op}' requires a number or a classification "
                f"literal (one of {sorted(CLASSIFICATION_ORDER)})"
            )
        if self.op in {Operator.IN, Operator.NOT_IN} and not isinstance(self.value, list):
            raise ValueError(f"operator '{self.op}' requires a list value")
        return self


class Rule(BaseModel):
    """A named, prioritised rule: if every ``when`` condition holds, apply ``effect``."""

    model_config = _STRICT

    id: str
    effect: Effect
    when: list[Condition] = []
    priority: int = 0
    description: str = ""


class RoleDef(BaseModel):
    """Role inheritance: a role transitively gains the roles it ``inherits``."""

    model_config = _STRICT

    inherits: list[str] = []


class Policy(BaseModel):
    """A complete, validated policy document."""

    model_config = _STRICT

    version: int = 1
    default_effect: Effect = Effect.ALLOW
    roles: dict[str, RoleDef] = {}
    rules: list[Rule] = []

    @model_validator(mode="after")
    def _validate_unique_ids(self) -> Policy:
        ids = [r.id for r in self.rules]
        if len(ids) != len(set(ids)):
            raise ValueError("rule ids must be unique")
        return self

    def expand_roles(self, role: str) -> list[str]:
        """Return ``role`` plus all roles it transitively inherits (cycle-safe)."""
        seen: list[str] = []
        stack = [role]
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.append(current)
            stack.extend(self.roles.get(current, RoleDef()).inherits)
        return seen

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Policy:
        return cls.model_validate(data)


__all__ = [
    "CLASSIFICATION_ORDER",
    "Condition",
    "Effect",
    "Operator",
    "Policy",
    "RoleDef",
    "Rule",
]
