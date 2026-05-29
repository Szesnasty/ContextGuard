"""guard() enrichment + redaction + token-budget tests (Milestone A4)."""

from __future__ import annotations

from pathlib import Path

from contextguard.core import ContextGuard
from contextguard.core.types import Chunk, Classification, Outcome, UserContext

POLICY_PATH = Path(__file__).resolve().parents[4] / "data" / "policies" / "example.yaml"


def _user() -> UserContext:
    return UserContext(sub="u1", tenant="acme", role="analyst", purpose="support")


def _chunk(cid: str, text: str, classification: Classification = Classification.INTERNAL) -> Chunk:
    return Chunk(id=cid, doc_id="d1", tenant="acme", text=text, classification=classification)


def test_chunk_with_secret_is_redacted_not_blocked() -> None:
    chunks = [_chunk("c1", "deploy key sk-abcdefghij0123456789 rotate it")]
    result = ContextGuard.from_policy(POLICY_PATH).guard(_user(), "q", chunks)
    assert len(result.allowed_chunks) == 1
    out = result.allowed_chunks[0].text
    assert "sk-abcdefghij0123456789" not in out
    assert "[REDACTED:SECRET]" in out
    assert result.decisions[0].outcome is Outcome.REDACTED
    assert result.decisions[0].policies_triggered == ["redact-secrets"]


def test_evidence_never_contains_the_secret() -> None:
    chunks = [_chunk("c1", "token sk-abcdefghij0123456789")]
    guard = ContextGuard.from_policy(POLICY_PATH)
    guard.guard(_user(), "q", chunks)
    ev = guard.last_evidence()
    assert ev is not None
    assert "sk-abcdefghij0123456789" not in str(ev)


def test_redaction_masks_without_leaking_in_context() -> None:
    chunks = [_chunk("c1", "secret sk-abcdefghij0123456789 " + "word " * 20)]
    result = ContextGuard.from_policy(POLICY_PATH).guard(_user(), "q", chunks)
    text = result.allowed_chunks[0].text
    assert "sk-abcdefghij0123456789" not in text
    assert text.count("[REDACTED") == 1  # overlapping spans coalesced into one mask
    assert result.tokens_before > 0


def test_clean_chunk_passes_unredacted() -> None:
    chunks = [_chunk("c1", "the quarterly summary is attached")]
    result = ContextGuard.from_policy(POLICY_PATH).guard(_user(), "q", chunks)
    assert result.decisions[0].outcome is Outcome.ALLOWED
    assert result.allowed_chunks[0].text == "the quarterly summary is attached"


def test_token_budget_drops_lowest_ranked() -> None:
    chunks = [
        _chunk("c1", "alpha " * 10),
        _chunk("c2", "beta " * 10),
        _chunk("c3", "gamma " * 10),
    ]
    guard = ContextGuard.from_policy(POLICY_PATH, token_budget=15)
    result = guard.guard(_user(), "q", chunks)
    kept = {c.id for c in result.allowed_chunks}
    assert "c1" in kept
    assert "c3" not in kept  # dropped by budget
    dropped = next(d for d in result.decisions if d.chunk_id == "c3")
    assert dropped.outcome is Outcome.BLOCKED
    assert "token-budget-exceeded" in dropped.reasons
    assert result.tokens_after <= 15
