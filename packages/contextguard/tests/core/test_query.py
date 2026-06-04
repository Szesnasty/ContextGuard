"""Core tier: ``/v1/query`` endpoint logic, in-process, no network (B1.6).

The retriever, gateway, and guard are injected via ``app.dependency_overrides``
with in-process fakes, so the full retrieve -> guard -> prompt -> answer flow is
exercised without a database or a live model (ADR-004 testability, ADR-010).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
from contextguard.api.deps import get_context_guard, get_llm_gateway, get_retriever
from contextguard.core import ContextGuard
from contextguard.llm.gateway import Completion
from contextguard_contracts import (
    Chunk,
    ChunkDecision,
    GuardedContext,
    Outcome,
    QueryResponse,
    UserContext,
)
from fastapi.testclient import TestClient


@dataclass(frozen=True)
class _Hit:
    id: str
    doc_id: str
    tenant: str
    classification: str
    text: str
    score: float
    metadata: dict[str, str] = field(default_factory=dict)


_HITS = [
    _Hit("c1", "doc-1", "acme", "internal", "Project Falcon launch code is FALCON-7788.", 0.9),
    _Hit("c2", "doc-2", "acme", "internal", "The finance team meets on Tuesdays.", 0.4),
]


class _FakeRetriever:
    def __init__(self, hits: list[_Hit] | None = None) -> None:
        self._hits = _HITS if hits is None else hits
        self.calls: list[tuple[str, int]] = []

    def retrieve(self, query: str, k: int = 5, filters: Any = None) -> list[_Hit]:
        self.calls.append((query, k))
        return self._hits[:k]


class _FakeGateway:
    model = "fake-model"

    def __init__(self, text: str = "Grounded answer [1].") -> None:
        self._text = text

    def complete(self, messages: list[dict[str, str]]) -> Completion:
        return Completion(text=self._text, model=self.model, prompt_tokens=11, completion_tokens=7)


class _SpyGuard:
    """Records the guard call, then delegates to a real pass-through guard."""

    def __init__(self) -> None:
        self._inner = ContextGuard()
        self.calls: list[tuple[UserContext, str, int]] = []

    def guard(self, user: UserContext, query: str, candidate_chunks: list[Chunk]) -> Any:
        self.calls.append((user, query, len(candidate_chunks)))
        return self._inner.guard(user, query, candidate_chunks)


class _BlockFirstGuard:
    """Blocks the first hit so the response-scrubbing contract is testable."""

    def guard(self, user: UserContext, query: str, candidate_chunks: list[Chunk]) -> GuardedContext:
        return GuardedContext(
            allowed_chunks=candidate_chunks[1:],
            decisions=[
                ChunkDecision(
                    chunk_id=candidate_chunks[0].id,
                    outcome=Outcome.BLOCKED,
                    reasons=["rule:test-block"],
                    policies_triggered=["test-block"],
                ),
                *[
                    ChunkDecision(
                        chunk_id=chunk.id,
                        outcome=Outcome.ALLOWED,
                        reasons=["passthrough"],
                    )
                    for chunk in candidate_chunks[1:]
                ],
            ],
            tokens_before=9,
            tokens_after=5,
        )


def _override(client: TestClient, **deps: Any) -> None:
    mapping = {
        get_retriever: deps.get("retriever", _FakeRetriever()),
        get_context_guard: deps.get("guard", ContextGuard()),
        get_llm_gateway: deps.get("gateway", _FakeGateway()),
    }
    for dep, value in mapping.items():
        client.app.dependency_overrides[dep] = _const(value)


def _const(value: Any) -> Any:
    """Zero-arg provider returning ``value`` (a clean FastAPI override)."""
    return lambda: value


_VALID_USER = UserContext(sub="u1", tenant="acme", role="sales", purpose="support")


def _auth(user: UserContext = _VALID_USER) -> dict[str, str]:
    """Authorization header carrying a signed token for ``user`` (ADR-015)."""
    from contextguard.auth import issue_token

    return {"Authorization": f"Bearer {issue_token(user)}"}


def _request(query: str = "What is the launch code?", k: int = 5) -> dict[str, Any]:
    return {"query": query, "k": k}


def test_query_happy_path(client: TestClient) -> None:
    _override(client)
    resp = client.post("/v1/query", json=_request(), headers=_auth())
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == "Grounded answer [1]."
    assert len(body["retrieved_chunks"]) == 2
    # Pass-through guard lets every retrieved chunk reach the context.
    assert len(body["guarded_context"]["allowed_chunks"]) == 2


def test_query_response_validates_against_contract(client: TestClient) -> None:
    _override(client)
    resp = client.post("/v1/query", json=_request(), headers=_auth())
    assert resp.status_code == 200
    parsed = QueryResponse.model_validate(resp.json())
    assert parsed.retrieved_chunks[0].id == "c1"
    assert parsed.retrieved_chunks[0].score == pytest.approx(0.9)


def test_query_response_withholds_blocked_chunk_text(client: TestClient) -> None:
    _override(client, guard=_BlockFirstGuard())
    resp = client.post("/v1/query", json=_request(), headers=_auth())
    assert resp.status_code == 200
    body = resp.json()

    blocked = body["retrieved_chunks"][0]
    assert blocked["id"] == "c1"
    assert blocked["doc_id"] == "doc-1"
    assert "FALCON-7788" not in blocked["text"]
    assert "withheld by ContextGuard" in blocked["text"]
    assert body["retrieved_chunks"][1]["text"] == "The finance team meets on Tuesdays."


def test_query_calls_guard(client: TestClient) -> None:
    spy = _SpyGuard()
    _override(client, guard=spy)
    resp = client.post("/v1/query", json=_request(), headers=_auth())
    assert resp.status_code == 200
    assert len(spy.calls) == 1


def test_query_user_context_parsed_and_attached(client: TestClient) -> None:
    spy = _SpyGuard()
    _override(client, guard=spy)
    client.post("/v1/query", json=_request(), headers=_auth())
    user, query, n_chunks = spy.calls[0]
    assert isinstance(user, UserContext)
    assert user.sub == "u1"
    assert user.tenant == "acme"
    assert user.role == "sales"
    assert query == "What is the launch code?"
    assert n_chunks == 2


def test_query_retrieves_only_k(client: TestClient) -> None:
    retriever = _FakeRetriever()
    _override(client, retriever=retriever)
    client.post("/v1/query", json=_request(k=1), headers=_auth())
    assert retriever.calls == [("What is the launch code?", 1)]


def test_query_model_failure_returns_clean_5xx(client: TestClient) -> None:
    class _BoomGateway:
        model = "boom"

        def complete(self, messages: list[dict[str, str]]) -> Completion:
            raise RuntimeError("ollama exploded: secret-token-xyz")

    _override(client, gateway=_BoomGateway())
    resp = client.post("/v1/query", json=_request(), headers=_auth())
    assert resp.status_code == 502
    detail = resp.json()["detail"]
    assert detail["trace_id"]
    # No stack trace and no internal error text leaks to the client.
    assert "Traceback" not in resp.text
    assert "secret-token-xyz" not in resp.text


def test_query_retrieval_failure_returns_clean_5xx(client: TestClient) -> None:
    class _BoomRetriever:
        def retrieve(self, query: str, k: int = 5, filters: Any = None) -> list[_Hit]:
            raise RuntimeError("db down")

    _override(client, retriever=_BoomRetriever())
    resp = client.post("/v1/query", json=_request(), headers=_auth())
    assert resp.status_code == 503
    assert resp.json()["detail"]["trace_id"]
    assert "Traceback" not in resp.text


def test_query_empty_query_rejected(client: TestClient) -> None:
    _override(client)
    resp = client.post("/v1/query", json=_request(query=""), headers=_auth())
    assert resp.status_code == 422


def test_query_without_token_rejected(client: TestClient) -> None:
    _override(client)
    resp = client.post("/v1/query", json=_request())
    assert resp.status_code in (401, 403)  # no Authorization header


def test_query_invalid_token_rejected(client: TestClient) -> None:
    _override(client)
    resp = client.post("/v1/query", json=_request(), headers={"Authorization": "Bearer not-a-jwt"})
    assert resp.status_code == 401
    # Identity can no longer be asserted via the request body.
    resp_body = client.post(
        "/v1/query",
        json={
            "query": "hi",
            "user": {"sub": "x", "tenant": "acme", "role": "admin", "purpose": "dev"},
        },
    )
    assert resp_body.status_code in (401, 403)


def test_query_types_present_in_openapi(client: TestClient) -> None:
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    assert "QueryRequest" in schemas
    assert "QueryResponse" in schemas
    assert "RetrievedChunk" in schemas
