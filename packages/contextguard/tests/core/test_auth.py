"""JWT identity stub tests (Milestone B3.2, ADR-015).

Identity comes from a *signed* token, not the request body: a valid token
round-trips to the right UserContext, and any tampering / expiry / missing claim
fails verification. Pure, offline (PyJWT is the only dependency).
"""

from __future__ import annotations

import time

import pytest
from contextguard.auth import AuthError, decode_token, issue_token
from contextguard_contracts import UserContext


def _user() -> UserContext:
    return UserContext(sub="sales@acme", tenant="acme", role="sales", purpose="support")


def test_issue_then_decode_round_trips() -> None:
    token = issue_token(_user(), secret="s3cret")
    decoded = decode_token(token, secret="s3cret")
    assert decoded == _user()


def test_tampered_token_fails_verification() -> None:
    token = issue_token(_user(), secret="s3cret")
    # Flip a character in the signature segment.
    head, payload, sig = token.split(".")
    tampered = f"{head}.{payload}.{sig[:-1]}{'A' if sig[-1] != 'A' else 'B'}"
    with pytest.raises(AuthError):
        decode_token(tampered, secret="s3cret")


def test_wrong_secret_fails_verification() -> None:
    token = issue_token(_user(), secret="s3cret")
    with pytest.raises(AuthError):
        decode_token(token, secret="other-secret")


def test_expired_token_fails_verification() -> None:
    past = int(time.time()) - 7200
    token = issue_token(_user(), secret="s3cret", ttl_seconds=3600, now=past)
    with pytest.raises(AuthError):
        decode_token(token, secret="s3cret")


def test_garbage_token_fails_verification() -> None:
    with pytest.raises(AuthError):
        decode_token("not-a-jwt", secret="s3cret")


def test_missing_claim_fails_verification() -> None:
    import jwt

    # A correctly-signed token that is missing the required 'tenant' claim.
    token = jwt.encode(
        {"sub": "x", "role": "sales", "purpose": "support", "exp": int(time.time()) + 60},
        "s3cret",
        algorithm="HS256",
    )
    with pytest.raises(AuthError):
        decode_token(token, secret="s3cret")
