"""Shared pytest fixtures for the API test tiers.

Test tiers (ADR-004 testability):
- tests/core/        — pure, zero external deps, zero network/frameworks-infra.
- tests/integration/ — needs the compose stack (`@pytest.mark.integration`).
- tests/e2e/         — full flow (`@pytest.mark.e2e`).
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from contextguard.api.app import create_app
from fastapi.testclient import TestClient
from hypothesis import settings

# Hypothesis profiles: CI runs more examples and derandomizes so failures are
# reproducible from the printed seed; dev stays fast.
settings.register_profile("ci", max_examples=300, derandomize=True)
settings.register_profile("dev", max_examples=50)
settings.load_profile("ci" if os.getenv("CI") else "dev")


@pytest.fixture
def client() -> Iterator[TestClient]:
    """In-process TestClient — no network, no server."""
    with TestClient(create_app()) as c:
        yield c
