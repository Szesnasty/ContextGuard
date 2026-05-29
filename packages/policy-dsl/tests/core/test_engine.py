"""Policy evaluator tests (step 4.2)."""

from __future__ import annotations

from contextguard_policy_dsl import Effect, Policy, PolicyEngine

POLICY = Policy.from_dict(
    {
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
                "priority": 50,
                "when": [
                    {"field": "user.roles", "op": "contains", "value": "sales"},
                    {"field": "chunk.classification", "op": "gte", "value": "confidential"},
                ],
            },
        ],
    }
)


def _ctx(
    *, user_tenant: str, roles: list[str], chunk_tenant: str, classification: str
) -> dict[str, object]:
    return {
        "user": {"tenant": user_tenant, "roles": roles, "role": roles[0]},
        "chunk": {"tenant": chunk_tenant, "classification": classification},
    }


def test_default_allow_when_no_rule_matches() -> None:
    engine = PolicyEngine(POLICY)
    decision = engine.evaluate(
        _ctx(user_tenant="acme", roles=["engineer"], chunk_tenant="acme", classification="public")
    )
    assert decision.effect is Effect.ALLOW
    assert decision.matched_rule_id is None
    assert decision.reasons == ["default-effect"]


def test_tenant_isolation_denies_cross_tenant() -> None:
    engine = PolicyEngine(POLICY)
    decision = engine.evaluate(
        _ctx(
            user_tenant="acme", roles=["engineer"], chunk_tenant="contoso", classification="public"
        )
    )
    assert decision.effect is Effect.DENY
    assert decision.matched_rule_id == "tenant-isolation"


def test_sales_blocked_from_confidential() -> None:
    engine = PolicyEngine(POLICY)
    decision = engine.evaluate(
        _ctx(
            user_tenant="acme", roles=["sales"], chunk_tenant="acme", classification="confidential"
        )
    )
    assert decision.effect is Effect.DENY
    assert decision.matched_rule_id == "sales-no-confidential"


def test_sales_allowed_internal() -> None:
    engine = PolicyEngine(POLICY)
    decision = engine.evaluate(
        _ctx(user_tenant="acme", roles=["sales"], chunk_tenant="acme", classification="internal")
    )
    assert decision.effect is Effect.ALLOW


def test_role_inheritance_manager_inherits_sales_block() -> None:
    engine = PolicyEngine(POLICY)
    # manager inherits sales -> roles list includes both (built by the bridge)
    decision = engine.evaluate(
        _ctx(
            user_tenant="acme",
            roles=["manager", "sales"],
            chunk_tenant="acme",
            classification="restricted",
        )
    )
    assert decision.effect is Effect.DENY
    assert decision.matched_rule_id == "sales-no-confidential"


def test_priority_tenant_isolation_wins() -> None:
    """Cross-tenant confidential matches both rules; higher priority wins."""
    engine = PolicyEngine(POLICY)
    decision = engine.evaluate(
        _ctx(
            user_tenant="acme",
            roles=["sales"],
            chunk_tenant="contoso",
            classification="confidential",
        )
    )
    assert decision.matched_rule_id == "tenant-isolation"


def test_missing_field_does_not_match() -> None:
    engine = PolicyEngine(POLICY)
    decision = engine.evaluate({"user": {"tenant": "acme", "roles": []}, "chunk": {}})
    # chunk.tenant missing -> neq cannot match; no rule fires -> default allow
    assert decision.effect is Effect.ALLOW


def test_deterministic() -> None:
    engine = PolicyEngine(POLICY)
    ctx = _ctx(
        user_tenant="acme", roles=["sales"], chunk_tenant="acme", classification="confidential"
    )
    assert engine.evaluate(ctx) == engine.evaluate(ctx)


def test_redact_effect() -> None:
    policy = Policy.from_dict(
        {
            "rules": [
                {
                    "id": "redact-internal",
                    "effect": "redact",
                    "when": [{"field": "chunk.classification", "op": "eq", "value": "internal"}],
                }
            ]
        }
    )
    decision = PolicyEngine(policy).evaluate(
        {"user": {"roles": []}, "chunk": {"classification": "internal"}}
    )
    assert decision.effect is Effect.REDACT


def test_numeric_ordered_comparison() -> None:
    policy = Policy.from_dict(
        {
            "rules": [
                {
                    "id": "redact-secrets",
                    "effect": "redact",
                    "when": [{"field": "chunk.secret_count", "op": "gte", "value": 1}],
                }
            ]
        }
    )
    engine = PolicyEngine(policy)
    assert engine.evaluate({"user": {}, "chunk": {"secret_count": 2}}).effect is Effect.REDACT
    assert engine.evaluate({"user": {}, "chunk": {"secret_count": 0}}).effect is Effect.ALLOW


def test_ordered_comparison_missing_field_does_not_match() -> None:
    policy = Policy.from_dict(
        {
            "rules": [
                {
                    "id": "risky",
                    "effect": "deny",
                    "when": [{"field": "chunk.risk_score", "op": "gt", "value": 0.5}],
                }
            ]
        }
    )
    # field absent -> no match -> default allow
    assert PolicyEngine(policy).evaluate({"user": {}, "chunk": {}}).effect is Effect.ALLOW
