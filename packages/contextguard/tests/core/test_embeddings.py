"""Embedder backend tests (Milestone B1.3, ADR-008).

Pure/core tier: the backend selection and empty-input contracts are verified
without any network call (the HTTP/OpenAI clients are never reached). The live
dimension/determinism checks against a real model live in the integration tier.
"""

from __future__ import annotations

import pytest
from contextguard.retrieval import (
    CloudEmbedder,
    OllamaEmbedder,
    get_embedder,
)
from contextguard.retrieval.embeddings import OLLAMA_EMBED_DIM, OPENAI_EMBED_DIM


def test_backend_switch_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMBEDDINGS", "local")
    assert isinstance(get_embedder(), OllamaEmbedder)


def test_backend_switch_default_is_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EMBEDDINGS", raising=False)
    assert isinstance(get_embedder(), OllamaEmbedder)


def test_backend_switch_cloud(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMBEDDINGS", "cloud")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-used")
    assert isinstance(get_embedder(), CloudEmbedder)


def test_backend_switch_unknown_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMBEDDINGS", "bogus")
    with pytest.raises(ValueError, match="unknown EMBEDDINGS backend"):
        get_embedder()


def test_local_embedder_empty_returns_empty() -> None:
    """Embedding an empty list short-circuits before any network call."""
    assert OllamaEmbedder().embed([]) == []


def test_cloud_embedder_empty_returns_empty() -> None:
    assert CloudEmbedder(api_key="sk-test-not-used").embed([]) == []


def test_declared_dimensions() -> None:
    assert OllamaEmbedder().dimension == OLLAMA_EMBED_DIM == 768
    assert CloudEmbedder(api_key="sk-test").dimension == OPENAI_EMBED_DIM == 1536


def test_local_embedder_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_EMBED_MODEL", "custom-model")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://example:1234/")
    embedder = OllamaEmbedder()
    assert embedder.model == "custom-model"
    # trailing slash is normalised away
    assert embedder._base_url == "http://example:1234"
