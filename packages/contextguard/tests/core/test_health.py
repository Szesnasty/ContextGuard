"""Core tier: /health behaves, in-process, no network."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_ok(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_health_reports_version(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["version"], "version must be non-empty"
