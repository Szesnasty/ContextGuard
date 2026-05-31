"""Schema-snapshot drift tests (step 1.2).

These tests make the committed JSON Schema files the contract of record: any
change to a public model that alters its schema fails here until the snapshot is
regenerated deliberately (``make schemas``) and reviewed in the diff.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from contextguard_contracts import EVIDENCE_SCHEMA_VERSION, EvidenceRecord
from pydantic import BaseModel, ConfigDict

# Import the generator module from scripts/ without packaging it.
_SCRIPTS = Path(__file__).resolve().parents[4] / "scripts"
sys.path.insert(0, str(_SCRIPTS))
import gen_schemas  # type: ignore[import-not-found]  # noqa: E402

SCHEMA_DIR = gen_schemas.SCHEMA_DIR


def test_all_exported_schemas_exist() -> None:
    for name in gen_schemas.EXPORTED:
        assert (SCHEMA_DIR / f"{name}.schema.json").exists(), name


@pytest.mark.parametrize("name", list(gen_schemas.EXPORTED))
def test_schema_snapshot_matches(name: str) -> None:
    model = gen_schemas.EXPORTED[name]
    committed = (SCHEMA_DIR / f"{name}.schema.json").read_text(encoding="utf-8")
    assert gen_schemas.render_schema(model) == committed, (
        f"{name}.schema.json is stale — run `make schemas` and review the diff"
    )


def test_snapshot_test_detects_drift() -> None:
    """A changed model must produce a schema different from the committed one."""

    class DriftedEvidence(EvidenceRecord):
        model_config = ConfigDict(extra="forbid", frozen=True)
        extra_field: str = "drift"

    committed = (SCHEMA_DIR / "evidence.schema.json").read_text(encoding="utf-8")
    assert gen_schemas.render_schema(DriftedEvidence) != committed


def test_generator_idempotent(tmp_path: Path) -> None:
    first = gen_schemas.write_schemas(tmp_path)
    contents_1 = {p.name: p.read_text(encoding="utf-8") for p in first}
    gen_schemas.write_schemas(tmp_path)
    contents_2 = {p.name: p.read_text(encoding="utf-8") for p in first}
    assert contents_1 == contents_2


def test_schema_version_literal_matches_snapshot() -> None:
    committed = json.loads((SCHEMA_DIR / "evidence.schema.json").read_text(encoding="utf-8"))
    const = committed["properties"]["schema_version"].get("const")
    assert const == EVIDENCE_SCHEMA_VERSION == "1.0"


def test_render_schema_accepts_basemodel() -> None:
    assert isinstance(EvidenceRecord, type)
    assert issubclass(EvidenceRecord, BaseModel)
