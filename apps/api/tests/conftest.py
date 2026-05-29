"""Shared pytest fixtures for the API test tiers.

Test tiers (ADR-004 testability):
- tests/core/        — pure, zero external deps, zero network/frameworks-infra.
- tests/integration/ — needs the compose stack (`@pytest.mark.integration`).
- tests/e2e/         — full flow (`@pytest.mark.e2e`).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from contextguard.api.app import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    """In-process TestClient — no network, no server."""
    with TestClient(create_app()) as c:
        yield c
