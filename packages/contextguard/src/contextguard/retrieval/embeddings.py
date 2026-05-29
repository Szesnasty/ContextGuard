"""Embedding backends behind one interface (Milestone B1.3, ADR-008).

Two backends, one :class:`Embedder` protocol:

* :class:`OllamaEmbedder` - the **default**, a local model served by Ollama
  (``nomic-embed-text``). Offline-first (ADR-003): the model runs as a service,
  exactly like a production deployment, and nothing leaves the machine.
* :class:`CloudEmbedder` - an optional upgrade backed by OpenAI
  (``text-embedding-3-small``), selected only when explicitly configured.

The backend is chosen by the ``EMBEDDINGS`` environment variable (``local`` by
default). Heavy clients (``httpx``, ``openai``) are imported lazily so importing
this module never pulls a network stack until an embedder is actually used
(ADR-010).
"""

from __future__ import annotations

import os
from typing import Protocol, runtime_checkable

Vector = list[float]

# Output dimension of the default local model (nomic-embed-text). The pgvector
# column is sized to match (see ``db.models.EMBEDDING_DIM``).
OLLAMA_EMBED_DIM = 768
OPENAI_EMBED_DIM = 1536

_DEFAULT_OLLAMA_MODEL = "nomic-embed-text"
_DEFAULT_OLLAMA_URL = "http://localhost:11434"
_DEFAULT_OPENAI_MODEL = "text-embedding-3-small"


@runtime_checkable
class Embedder(Protocol):
    """Turns texts into dense vectors. Implementations must be batch-friendly."""

    @property
    def model(self) -> str: ...

    @property
    def dimension(self) -> int: ...

    def embed(self, texts: list[str]) -> list[Vector]: ...


class OllamaEmbedder:
    """Local, offline embedder backed by an Ollama-served model (default)."""

    def __init__(
        self,
        *,
        model: str | None = None,
        base_url: str | None = None,
        dimension: int = OLLAMA_EMBED_DIM,
        timeout: float = 60.0,
    ) -> None:
        self._model = model or os.getenv("OLLAMA_EMBED_MODEL") or _DEFAULT_OLLAMA_MODEL
        self._base_url = (base_url or os.getenv("OLLAMA_BASE_URL") or _DEFAULT_OLLAMA_URL).rstrip(
            "/"
        )
        self._dimension = dimension
        self._timeout = timeout

    @property
    def model(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: list[str]) -> list[Vector]:
        if not texts:
            return []
        import httpx

        resp = httpx.post(
            f"{self._base_url}/api/embed",
            json={"model": self._model, "input": texts},
            timeout=self._timeout,
        )
        resp.raise_for_status()
        embeddings = resp.json()["embeddings"]
        return [[float(x) for x in vector] for vector in embeddings]


class CloudEmbedder:
    """Optional cloud embedder (OpenAI). Used only when ``EMBEDDINGS=cloud``."""

    def __init__(
        self,
        *,
        model: str = _DEFAULT_OPENAI_MODEL,
        dimension: int = OPENAI_EMBED_DIM,
        api_key: str | None = None,
    ) -> None:
        self._model = model
        self._dimension = dimension
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")

    @property
    def model(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: list[str]) -> list[Vector]:
        if not texts:
            return []
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key)
        resp = client.embeddings.create(model=self._model, input=texts)
        return [list(item.embedding) for item in resp.data]


def get_embedder() -> Embedder:
    """Return the configured embedder. ``EMBEDDINGS=local`` (default) or ``cloud``."""
    backend = os.getenv("EMBEDDINGS", "local").lower()
    if backend == "local":
        return OllamaEmbedder()
    if backend == "cloud":
        return CloudEmbedder()
    msg = f"unknown EMBEDDINGS backend {backend!r} (expected 'local' or 'cloud')"
    raise ValueError(msg)


__all__ = [
    "OLLAMA_EMBED_DIM",
    "OPENAI_EMBED_DIM",
    "CloudEmbedder",
    "Embedder",
    "OllamaEmbedder",
    "Vector",
    "get_embedder",
]
