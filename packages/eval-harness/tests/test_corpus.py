"""Corpus-shape tests for the planted-leak demo corpus.

These assert the planted-leak corpus is well-formed and that MANIFEST.md,
users.yaml, and leak_queries.yaml agree with the files on disk. Pure, zero-infra:
they read files and parse YAML, nothing heavier.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml
from contextguard_contracts import Classification, UserContext
from contextguard_eval_harness.corpus import TENANTS_DIR, load_corpus

_REPO_ROOT = TENANTS_DIR.parent.parent
MANIFEST = TENANTS_DIR / "MANIFEST.md"
USERS_YAML = _REPO_ROOT / "data" / "users.yaml"
LEAK_QUERIES = _REPO_ROOT / "data" / "eval" / "leak_queries.yaml"


def _manifest_doc_ids() -> set[str]:
    text = MANIFEST.read_text(encoding="utf-8")
    # doc_ids appear in the second table column, e.g. "| acme-product-faq |".
    return set(re.findall(r"\b((?:acme|contoso)-[a-z0-9-]+)\b", text))


def test_corpus_loads() -> None:
    docs = load_corpus()
    assert len(docs) >= 13  # 9 acme + 5 contoso
    assert all(doc.text for doc in docs)


def test_manifest_complete() -> None:
    """Every file under data/tenants/** appears in MANIFEST.md by doc_id."""
    manifest_ids = _manifest_doc_ids()
    for doc in load_corpus():
        assert doc.doc_id in manifest_ids, f"{doc.doc_id} missing from MANIFEST.md"


def test_manifest_classifications_valid() -> None:
    """Every classification on disk is a valid Classification enum value."""
    for doc in load_corpus():
        assert isinstance(doc.classification, Classification)


def test_leak_target_exists() -> None:
    """At least one acme confidential leak target exists and is flagged."""
    targets = [
        d
        for d in load_corpus()
        if d.tenant == "acme"
        and d.classification is Classification.CONFIDENTIAL
        and d.is_leak_target
    ]
    assert targets, "no acme confidential leak target found"


def test_cross_tenant_trap_exists() -> None:
    """At least one contoso doc is flagged as a cross-tenant trap."""
    traps = [d for d in load_corpus() if d.tenant == "contoso" and d.is_cross_tenant_trap]
    assert traps, "no contoso cross-tenant trap found"


def test_users_yaml_schema() -> None:
    """Every users.yaml entry validates as a UserContext."""
    data = yaml.safe_load(USERS_YAML.read_text(encoding="utf-8"))
    users = data["users"]
    assert users
    for entry in users:
        user = UserContext(**entry)
        assert user.tenant in {"acme", "contoso"}


def test_leak_queries_reference_real_docs() -> None:
    """Each planted query targets a doc_id that exists, asked by a real user."""
    doc_ids = {d.doc_id for d in load_corpus()}
    users = {u["sub"] for u in yaml.safe_load(USERS_YAML.read_text(encoding="utf-8"))["users"]}
    queries = yaml.safe_load(LEAK_QUERIES.read_text(encoding="utf-8"))["queries"]
    assert queries
    for q in queries:
        assert q["expected_target"] in doc_ids, q["expected_target"]
        assert q["asked_by"] in users, q["asked_by"]


@pytest.mark.parametrize("path", sorted(TENANTS_DIR.glob("*/docs/*.md")), ids=lambda p: p.name)
def test_frontmatter_tenant_matches_folder(path: Path) -> None:
    """A doc's declared tenant matches the folder it lives in (no misfiled docs)."""
    from contextguard_eval_harness.corpus import parse_document

    doc = parse_document(path)
    assert doc.tenant == path.parents[1].name
