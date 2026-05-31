"""Dev model picker tests (dashboard convenience endpoints).

The model endpoints let the demo dashboard list the Ollama chat models, switch
the live one, and pull new ones. Like the token minter they are strictly
dev/demo and must refuse (403) once a real ``JWT_SECRET`` is configured. The
local Ollama is mocked, so these stay offline and infra-free.
"""

from __future__ import annotations

import httpx
import pytest
from contextguard.api.app import create_app
from fastapi.testclient import TestClient


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture(autouse=True)
def _clean_model_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OLLAMA_CHAT_MODEL", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)


def _mock_tags(monkeypatch: pytest.MonkeyPatch, names: list[str]) -> None:
    payload = {"models": [{"name": name, "size": 1_000_000_000} for name in names]}
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse(payload))


def test_lists_installed_models(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_tags(monkeypatch, ["llama3.2:3b", "qwen2.5:7b"])
    response = client.get("/v1/dev/models")
    assert response.status_code == 200

    body = response.json()
    names = {model["name"] for model in body["models"]}
    assert names == {"llama3.2:3b", "qwen2.5:7b"}
    assert "active" in body


def test_set_model_switches_active(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_tags(monkeypatch, ["llama3.2:3b", "qwen2.5:7b"])
    response = client.post("/v1/dev/model", json={"model": "qwen2.5:7b"})
    assert response.status_code == 200
    assert response.json()["model"] == "qwen2.5:7b"

    # The switch re-points the live query path via the env the gateway reads.
    follow = client.get("/v1/dev/models")
    assert follow.json()["active"] == "qwen2.5:7b"


def test_set_uninstalled_model_is_404(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_tags(monkeypatch, ["llama3.2:3b"])
    response = client.post("/v1/dev/model", json={"model": "not-pulled:70b"})
    assert response.status_code == 404


def test_pull_model_reports_status(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _FakeResponse({"status": "success"}))
    response = client.post("/v1/dev/models/pull", json={"model": "qwen2.5:7b"})
    assert response.status_code == 200
    assert response.json() == {"model": "qwen2.5:7b", "status": "success"}


def test_model_tools_disabled_when_real_secret(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("JWT_SECRET", "a-real-production-secret")
    assert client.get("/v1/dev/models").status_code == 403
    assert client.post("/v1/dev/model", json={"model": "x"}).status_code == 403
    assert client.post("/v1/dev/models/pull", json={"model": "x"}).status_code == 403
