"""The policy evaluator — pure, deterministic, zero I/O (ADR-003, ADR-005).

``PolicyEngine.evaluate(context)`` resolves a single ``allow``/``deny``/
``redact`` decision for one chunk against one user. The context is a plain
mapping (``{"user": {...}, "chunk": {...}}``) so the engine stays decoupled from
the domain models — the same reason the interface is OPA-swappable.

Determinism is a hard requirement: identical inputs always yield identical
decisions (property-tested). There is no randomness, no clock, no network.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from contextguard_policy_dsl.schema import (
    CLASSIFICATION_ORDER,
    Condition,
    Effect,
    Operator,
    Policy,
)

_MISSING = object()


@dataclass(frozen=True)
class PolicyDecision:
    """The verdict for one (user, chunk) pair."""

    effect: Effect
    matched_rule_id: str | None
    reasons: list[str] = field(default_factory=list)


def _resolve(context: Mapping[str, Any], path: str) -> Any:
    """Walk a dotted path (e.g. ``chunk.metadata.owner``) through nested maps."""
    current: Any = context
    for part in path.split("."):
        if isinstance(current, Mapping) and part in current:
            current = current[part]
        else:
            return _MISSING
    return current


def _rank(value: Any) -> int:
    if not isinstance(value, str) or value not in CLASSIFICATION_ORDER:
        raise ValueError(f"value {value!r} is not an ordered classification")
    return CLASSIFICATION_ORDER[value]


def _orderable(value: Any) -> float | int:
    """Map a value to a comparable number: numbers as-is, classification by rank."""
    if isinstance(value, bool):
        raise ValueError("booleans are not orderable")
    if isinstance(value, (int, float)):
        return value
    return _rank(value)


def _match(condition: Condition, context: Mapping[str, Any]) -> bool:
    left = _resolve(context, condition.field)
    if left is _MISSING:
        return False

    if condition.ref is not None:
        right = _resolve(context, condition.ref)
        if right is _MISSING:
            return False
    else:
        right = condition.value

    op = condition.op
    if op is Operator.EQ:
        return bool(left == right)
    if op is Operator.NEQ:
        return bool(left != right)
    if op is Operator.IN:
        return left in right
    if op is Operator.NOT_IN:
        return left not in right
    if op is Operator.CONTAINS:
        return isinstance(left, (list, tuple, set, str)) and right in left
    if op in {Operator.GT, Operator.GTE, Operator.LT, Operator.LTE}:
        try:
            lo, hi = _orderable(left), _orderable(right)
        except ValueError:
            return False
        if op is Operator.GT:
            return lo > hi
        if op is Operator.GTE:
            return lo >= hi
        if op is Operator.LT:
            return lo < hi
        return lo <= hi
    raise ValueError(f"unhandled operator: {op}")  # pragma: no cover


class PolicyEngine:
    """Evaluates a :class:`Policy` against a context mapping."""

    def __init__(self, policy: Policy) -> None:
        self.policy = policy
        # Stable, deterministic order: higher priority first, then declaration order.
        self._rules = sorted(enumerate(policy.rules), key=lambda pair: (-pair[1].priority, pair[0]))

    def evaluate(self, context: Mapping[str, Any]) -> PolicyDecision:
        for _, rule in self._rules:
            if all(_match(c, context) for c in rule.when):
                return PolicyDecision(
                    effect=rule.effect,
                    matched_rule_id=rule.id,
                    reasons=[f"rule:{rule.id}"],
                )
        return PolicyDecision(
            effect=self.policy.default_effect,
            matched_rule_id=None,
            reasons=["default-effect"],
        )


__all__ = ["PolicyDecision", "PolicyEngine"]
