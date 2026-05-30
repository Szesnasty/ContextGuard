"""Signed-token identity for the HTTP boundary (Milestone B3.2, ADR-015).

The baseline RAG path trusted a client-asserted ``user`` in the request body -
itself the vulnerability: anyone could claim to be ``legal@acme``. This module
moves identity to a **signed JWT**: the caller presents a token, the server
verifies the signature, and :class:`UserContext` is derived from the verified
claims (``sub``/``tenant``/``role``/``purpose``). A tampered or expired token
fails verification, so the body can no longer assert who the caller is.

This is a deliberate **stub** (ADR-015): one symmetric HS256 secret, no issuer
/ audience / key rotation, demo identities from ``data/users.yaml``. A real
OIDC / IdP integration is a future ADR. ``jwt`` (PyJWT) is imported lazily so
``import contextguard.auth`` stays light (it lives in the ``[api]`` tier).
"""

from __future__ import annotations

import os
import time

from contextguard_contracts import UserContext

DEFAULT_ALGORITHM = "HS256"
DEFAULT_TTL_SECONDS = 3600
# Dev-only fallback secret. Override with JWT_SECRET in any real deployment.
_DEFAULT_SECRET = "contextguard-dev-secret-do-not-use-in-prod"  # noqa: S105 - dev fallback
_REQUIRED_CLAIMS = ("sub", "tenant", "role", "purpose")


class AuthError(Exception):
    """Raised when a token is missing, malformed, tampered with, or expired."""


def _secret(secret: str | None) -> str:
    """Resolve the signing secret: explicit arg, then ``JWT_SECRET``, then dev fallback."""
    return secret or os.getenv("JWT_SECRET") or _DEFAULT_SECRET


def issue_token(
    user: UserContext,
    *,
    secret: str | None = None,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    now: int | None = None,
) -> str:
    """Issue a signed token carrying ``user``'s identity claims.

    ``now`` (epoch seconds) is injectable so tests can mint expired tokens
    deterministically. Demo/dev helper - production tokens come from an IdP.
    """
    import jwt

    issued = int(now if now is not None else time.time())
    payload = {
        "sub": user.sub,
        "tenant": user.tenant,
        "role": user.role,
        "purpose": user.purpose,
        "iat": issued,
        "exp": issued + ttl_seconds,
    }
    return jwt.encode(payload, _secret(secret), algorithm=DEFAULT_ALGORITHM)


def decode_token(token: str, *, secret: str | None = None) -> UserContext:
    """Verify ``token`` and derive a :class:`UserContext` from its claims.

    Raises :class:`AuthError` on any failure - bad signature (tampering), expiry,
    malformed token, or a missing required claim - so callers never have to tell
    the failure modes apart at the boundary (all map to 401).
    """
    import jwt

    try:
        claims = jwt.decode(token, _secret(secret), algorithms=[DEFAULT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise AuthError(f"token verification failed: {exc}") from exc

    missing = [c for c in _REQUIRED_CLAIMS if not claims.get(c)]
    if missing:
        raise AuthError(f"token is missing required claims: {missing}")

    return UserContext(
        sub=str(claims["sub"]),
        tenant=str(claims["tenant"]),
        role=str(claims["role"]),
        purpose=str(claims["purpose"]),
    )


__all__ = [
    "DEFAULT_ALGORITHM",
    "DEFAULT_TTL_SECONDS",
    "AuthError",
    "decode_token",
    "issue_token",
]
