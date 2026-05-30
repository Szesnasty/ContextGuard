"""Retrieval prefilter derivation tests (Milestone B3.1 - phase 4 push-down).

The policy is turned into structural predicates (tenant + allowed
classifications) pushed into retrieval *before* kNN, so unauthorised chunks
never enter the candidate set. Pure, zero-infra: policy DSL + contracts only.
"""

from __future__ import annotations

from pathlib import Path

from contextguard.retrieval.policy_filter import RetrievalFilter, build_retrieval_filter
from contextguard_contracts.models import UserContext
from contextguard_policy_dsl import Policy

POLICY_PATH = Path(__file__).resolve().parents[4] / "data" / "policies" / "example.yaml"


def _policy() -> Policy:
    import yaml

    return Policy.from_dict(yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8")))


def _user(role: str, tenant: str = "acme") -> UserContext:
    return UserContext(sub=f"{role}@{tenant}", tenant=tenant, role=role, purpose="support")


def test_sales_prefilter_excludes_confidential_and_pins_tenant() -> None:
    f = build_retrieval_filter(_policy(), _user("sales"))
    assert isinstance(f, RetrievalFilter)
    assert f.tenant == "acme"
    assert f.allowed_classifications == ("public", "internal")


def test_legal_prefilter_allows_all_classifications() -> None:
    f = build_retrieval_filter(_policy(), _user("legal"))
    assert f.allowed_classifications == ("public", "internal", "confidential", "restricted")


def test_prefilter_tenant_isolates_contoso_user() -> None:
    f = build_retrieval_filter(_policy(), _user("sales", tenant="contoso"))
    assert f.tenant == "contoso"
    # sales gate still applies regardless of tenant
    assert f.allowed_classifications == ("public", "internal")


def test_manager_inherits_sales_gate() -> None:
    f = build_retrieval_filter(_policy(), _user("manager"))
    assert f.allowed_classifications == ("public", "internal")
