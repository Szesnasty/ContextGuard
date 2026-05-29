"""Core type re-export surface tests (step 1.3)."""

from __future__ import annotations

import ast
from pathlib import Path

import contextguard_contracts as cc
from contextguard.core import types as core_types

EXPECTED = [
    "UserContext",
    "Chunk",
    "ChunkDecision",
    "GuardedContext",
    "EvidenceRecord",
    "EvidenceMetrics",
    "Span",
    "RiskSignal",
    "Classification",
    "Outcome",
    "RiskType",
    "SpanType",
]

CORE_DIR = Path(core_types.__file__).resolve().parent


def test_core_types_surface_complete() -> None:
    for name in EXPECTED:
        assert hasattr(core_types, name), name


def test_core_types_are_reexports_not_copies() -> None:
    assert core_types.Chunk is cc.Chunk
    assert core_types.EvidenceRecord is cc.EvidenceRecord
    assert core_types.UserContext is cc.UserContext


def test_core_submodules_do_not_import_contracts_directly() -> None:
    """Only ``core/types.py`` may import ``contextguard_contracts``."""
    offenders: list[str] = []
    for path in CORE_DIR.glob("*.py"):
        if path.name == "types.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
                "contextguard_contracts"
            ):
                offenders.append(path.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("contextguard_contracts"):
                        offenders.append(path.name)
    assert offenders == [], f"direct contracts imports in core: {offenders}"
