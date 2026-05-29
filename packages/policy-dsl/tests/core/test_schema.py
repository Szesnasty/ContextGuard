"""Policy DSL schema validation tests (step 4.1)."""

from __future__ import annotations

import pytest
from contextguard_policy_dsl import (
    Condition,
    Effect,
    Operator,
    Policy,
    Rule,
)
from pydantic import ValidationError

SAMPLE = {
    "version": 1,
    "default_effect": "allow",
    "roles": {"manager": {"inherits": ["sales"]}},
    "rules": [
        {
            "id": "tenant-isolation",
            "effect": "deny",
            "priority": 100,
            "when": [{"field": "chunk.tenant", "op": "neq", "ref": "user.tenant"}],
        },
        {
            "id": "sales-no-confidential",
            "effect": "deny",
            "when": [
                {"field": "user.roles", "op": "contains", "value": "sales"},
                {"field": "chunk.classification", "op": "gte", "value": "confidential"},
            ],
        },
    ],
}


def test_sample_policy_validates() -> None:
    policy = Policy.from_dict(SAMPLE)
    assert policy.version == 1
    assert policy.default_effect is Effect.ALLOW
    assert len(policy.rules) == 2
    assert isinstance(policy.rules[0], Rule)


def test_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        Policy.from_dict({"version": 1, "bogus": True})


def test_duplicate_rule_ids_rejected() -> None:
    data = {
        "rules": [
            {"id": "dup", "effect": "deny", "when": []},
            {"id": "dup", "effect": "allow", "when": []},
        ]
    }
    with pytest.raises(ValidationError, match="unique"):
        Policy.from_dict(data)


def test_condition_value_xor_ref() -> None:
    with pytest.raises(ValidationError, match="both"):
        Condition(field="a", op=Operator.EQ, value="x", ref="b")
    with pytest.raises(ValidationError, match="either"):
        Condition(field="a", op=Operator.EQ)


def test_ref_only_for_eq_neq() -> None:
    Condition(field="chunk.tenant", op=Operator.NEQ, ref="user.tenant")  # ok
    with pytest.raises(ValidationError, match="ref"):
        Condition(field="a", op=Operator.IN, ref="b")


def test_ordered_op_requires_classification_literal() -> None:
    Condition(field="chunk.classification", op=Operator.GTE, value="confidential")  # ok
    with pytest.raises(ValidationError, match="classification"):
        Condition(field="chunk.classification", op=Operator.GTE, value="nonsense")


def test_ordered_op_accepts_number() -> None:
    Condition(field="chunk.secret_count", op=Operator.GTE, value=1)  # ok
    Condition(field="chunk.risk_score", op=Operator.GT, value=0.5)  # ok
    with pytest.raises(ValidationError, match="number or a classification"):
        Condition(field="chunk.secret_count", op=Operator.GTE, value=True)


def test_in_requires_list() -> None:
    Condition(field="user.role", op=Operator.IN, value=["a", "b"])  # ok
    with pytest.raises(ValidationError, match="list"):
        Condition(field="user.role", op=Operator.IN, value="a")


def test_expand_roles_transitive_and_cycle_safe() -> None:
    policy = Policy.from_dict(
        {
            "roles": {
                "manager": {"inherits": ["sales"]},
                "sales": {"inherits": ["base"]},
                "base": {"inherits": ["manager"]},  # cycle
            }
        }
    )
    expanded = set(policy.expand_roles("manager"))
    assert expanded == {"manager", "sales", "base"}


def test_expand_roles_unknown_role() -> None:
    policy = Policy.from_dict({})
    assert policy.expand_roles("ghost") == ["ghost"]
