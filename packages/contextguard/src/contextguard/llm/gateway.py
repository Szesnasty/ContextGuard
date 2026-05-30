"""LLM gateway behind one interface (Milestone B1.5, ADR-014).

Mirrors the embedder design (ADR-008): two backends, one :class:`LLMGateway`
protocol, selected by an environment variable. The default is a local model
served by Ollama (``qwen2.5:7b``) - offline-first (ADR-003), model-as-a-service,
nothing leaves the machine. A cloud upgrade (OpenAI) slots in behind the same
protocol when explicitly configured.

LiteLLM is the documented production swap for provider-agnostic routing and
fallback (plan topic 11); it would implement this same :class:`LLMGateway`
without touching callers (ADR-004). It is deliberately *not* the default - see
ADR-014 - to keep the dependency surface small and consistent with B1.3.

Heavy clients (``httpx``, ``openai``) are imported lazily so importing this
module never pulls a network stack until a gateway is actually used (ADR-010).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

# One chat message in the OpenAI/LiteLLM shape: {"role": ..., "content": ...}.
Message = dict[str, str]

_DEFAULT_OLLAMA_MODEL = "qwen2.5:7b"
_DEFAULT_OLLAMA_URL = "http://localhost:11434"
_DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


@dataclass(frozen=True)
class Completion:
    """A model reply plus the token usage needed for evidence and cost (B4)."""

    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int


@runtime_checkable
class LLMGateway(Protocol):
    """Turns chat messages into a completion. Implementations stay stateless."""

    @property
    def model(self) -> str: ...

    def complete(self, messages: list[Message]) -> Completion: ...


class OllamaGateway:
    """Local, offline gateway backed by an Ollama-served chat model (default)."""

    def __init__(
        self,
        *,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self._model = model or os.getenv("OLLAMA_CHAT_MODEL") or _DEFAULT_OLLAMA_MODEL
        self._base_url = (base_url or os.getenv("OLLAMA_BASE_URL") or _DEFAULT_OLLAMA_URL).rstrip(
            "/"
        )
        self._timeout = timeout

    @property
    def model(self) -> str:
        return self._model

    def complete(self, messages: list[Message]) -> Completion:
        import httpx

        resp = httpx.post(
            f"{self._base_url}/api/chat",
            json={"model": self._model, "messages": messages, "stream": False},
            timeout=self._timeout,
        )
        resp.raise_for_status()
        body = resp.json()
        return Completion(
            text=body["message"]["content"],
            model=self._model,
            prompt_tokens=int(body.get("prompt_eval_count", 0)),
            completion_tokens=int(body.get("eval_count", 0)),
        )


class CloudGateway:
    """Optional cloud gateway (OpenAI). Used only when ``LLM=cloud``."""

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self._model = model or os.getenv("OPENAI_CHAT_MODEL") or _DEFAULT_OPENAI_MODEL
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")

    @property
    def model(self) -> str:
        return self._model

    def complete(self, messages: list[Message]) -> Completion:
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key)
        resp = client.chat.completions.create(model=self._model, messages=messages)  # type: ignore[arg-type]
        usage = resp.usage
        return Completion(
            text=resp.choices[0].message.content or "",
            model=self._model,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
        )


def get_gateway() -> LLMGateway:
    """Return the configured gateway. ``LLM=local`` (default) or ``cloud``."""
    backend = (os.getenv("LLM") or "local").lower()
    if backend == "local":
        return OllamaGateway()
    if backend == "cloud":
        return CloudGateway()
    raise ValueError(f"unknown LLM backend: {backend!r} (expected 'local' or 'cloud')")


__all__ = [
    "CloudGateway",
    "Completion",
    "LLMGateway",
    "Message",
    "OllamaGateway",
    "get_gateway",
]
