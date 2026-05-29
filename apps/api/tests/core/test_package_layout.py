"""Core tier: every declared subpackage is importable.

This guards the package boundary ADR-004 polices — the layout that step 0.6's
import-gate will later enforce dependency rules over.
"""

from __future__ import annotations

import importlib

import pytest

SUBPACKAGES = [
    "contextguard",
    "contextguard.core",
    "contextguard.retrieval",
    "contextguard.policy",
    "contextguard.redaction",
    "contextguard.risk",
    "contextguard.evidence",
    "contextguard.llm",
    "contextguard.api",
    "contextguard.db",
    "contextguard.jobs",
    "contextguard.observability",
]


@pytest.mark.parametrize("name", SUBPACKAGES)
def test_subpackage_importable(name: str) -> None:
    assert importlib.import_module(name) is not None
