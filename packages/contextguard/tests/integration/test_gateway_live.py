"""LLM gateway integration tests (Milestone B1.5, ADR-014).

Opt-in: require the compose stack (`make up`) with the chat model pulled. They
SKIP when the stack is down so `make test` stays green offline (ADR-010).

    make up && uv run pytest packages/contextguard/tests/integration -m integration
"""

from __future__ import annotations

import socket

import pytest

pytestmark = pytest.mark.integration

OLLAMA_PORT = 11434


def _port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


requires_ollama = pytest.mark.skipif(
    not _port_open("localhost", OLLAMA_PORT),
    reason="local Ollama not running (run `make up`)",
)


@requires_ollama
def test_gateway_answers_offline() -> None:
    from contextguard.llm.gateway import OllamaGateway

    gateway = OllamaGateway()
    result = gateway.complete([{"role": "user", "content": "Reply with the single word: ready"}])
    assert result.text.strip()  # non-empty answer
    assert result.prompt_tokens > 0
    assert result.completion_tokens > 0
    assert result.model


@requires_ollama
def test_grounded_answer_uses_context() -> None:
    from contextguard.llm.gateway import OllamaGateway
    from contextguard.retrieval.prompt import build_prompt

    class _Chunk:
        id = "acme-secret-1"
        text = "The launch code for Project Falcon is FALCON-7788."

    messages = build_prompt("What is the launch code for Project Falcon?", [_Chunk()])
    result = OllamaGateway().complete(messages)
    # The model should surface the planted code from the provided context.
    assert "FALCON-7788" in result.text


@requires_ollama
def test_empty_context_does_not_fabricate() -> None:
    from contextguard.llm.gateway import OllamaGateway
    from contextguard.retrieval.prompt import build_prompt

    messages = build_prompt("What is the launch code for Project Falcon?", [])
    result = OllamaGateway().complete(messages)
    # With no context, the model must not invent the planted code.
    assert "FALCON-7788" not in result.text
