"""Dev token minter tests (dashboard convenience endpoint).

The minter issues a *valid* demo token for an identity in ``data/users.yaml`` so
the UI can offer a one-click button. It is strictly dev/demo: it must mint a
usable token while the dev fallback secret is in use, and **refuse** (403) the
moment a real ``JWT_SECRET`` is configured. Pure, offline (PyJWT + the on-disk
users file are the only inputs).
"""

from __future__ import annotations

import pytest
from contextguard.api.app import create_app
from contextguard.auth import decode_token
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_mint_returns_a_decodable_token(client: TestClient) -> None:
    response = client.post("/v1/dev/token", json={"sub": "sales@acme"})
    assert response.status_code == 200

    body = response.json()
    assert body["sub"] == "sales@acme"
    assert body["tenant"] == "acme"

    user = decode_token(body["token"])
    assert user.sub == "sales@acme"
    assert user.role == "sales"


def test_unknown_identity_is_404(client: TestClient) -> None:
    response = client.post("/v1/dev/token", json={"sub": "nobody@nowhere"})
    assert response.status_code == 404


def test_minting_disabled_when_real_secret_configured(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("JWT_SECRET", "a-real-production-secret")
    response = client.post("/v1/dev/token", json={"sub": "sales@acme"})
    assert response.status_code == 403


def test_lists_demo_identities(client: TestClient) -> None:
    response = client.get("/v1/dev/identities")
    assert response.status_code == 200
    subs = {entry["sub"] for entry in response.json()}
    assert "sales@acme" in subs
    assert "legal@acme" in subs
