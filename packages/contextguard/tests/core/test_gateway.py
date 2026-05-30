"""LLM gateway selection + token-capture tests (Milestone B1.5, ADR-014).

These stay zero-infra: the backend switch and the response parsing are tested
without a live model (the HTTP call is monkeypatched).
"""

from __future__ import annotations

import pytest
from contextguard.llm.gateway import (
    CloudGateway,
    Completion,
    OllamaGateway,
    get_gateway,
)


def test_default_backend_is_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM", raising=False)
    assert isinstance(get_gateway(), OllamaGateway)


def test_local_backend_selected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM", "local")
    assert isinstance(get_gateway(), OllamaGateway)


def test_cloud_backend_selected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM", "cloud")
    assert isinstance(get_gateway(), CloudGateway)


def test_unknown_backend_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM", "banana")
    with pytest.raises(ValueError):
        get_gateway()


def test_model_id_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_CHAT_MODEL", "llama3.2:3b")
    assert OllamaGateway().model == "llama3.2:3b"


def test_ollama_parses_text_and_token_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class _Resp:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "message": {"role": "assistant", "content": "Project Falcon is a deal."},
                "prompt_eval_count": 42,
                "eval_count": 7,
            }

    def _fake_post(url: str, **kwargs: object) -> _Resp:
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        return _Resp()

    import httpx

    monkeypatch.setattr(httpx, "post", _fake_post)

    gateway = OllamaGateway(model="qwen2.5:7b")
    result = gateway.complete([{"role": "user", "content": "What is Project Falcon?"}])

    assert isinstance(result, Completion)
    assert result.text == "Project Falcon is a deal."
    assert result.model == "qwen2.5:7b"
    assert result.prompt_tokens == 42
    assert result.completion_tokens == 7
    assert str(captured["url"]).endswith("/api/chat")
