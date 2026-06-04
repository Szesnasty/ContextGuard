"""ContextGuard policy DSL — schema + pure evaluator (zero-infra)."""

from __future__ import annotations

from contextguard_policy_dsl.engine import PolicyDecision, PolicyEngine
from contextguard_policy_dsl.schema import (
    CLASSIFICATION_ORDER,
    Condition,
    Effect,
    Operator,
    Policy,
    RoleDef,
    Rule,
)

__version__ = "1.0.0"

__all__ = [
    "CLASSIFICATION_ORDER",
    "Condition",
    "Effect",
    "Operator",
    "Policy",
    "PolicyDecision",
    "PolicyEngine",
    "RoleDef",
    "Rule",
    "__version__",
]
