"""HTTP authentication dependency: derive the user from a Bearer token (B3.2).

The single seam the request path uses to obtain the *authenticated* caller. The
``Authorization: Bearer <jwt>`` header is verified and mapped to a
:class:`UserContext`; a missing, tampered, or expired token is rejected at the
boundary with ``401`` and no internal detail. Identity is never taken from the
request body (ADR-015).
"""

from __future__ import annotations

from contextguard_contracts import UserContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from contextguard.auth import AuthError, decode_token

_bearer = HTTPBearer(description="Signed identity token (ADR-015 stub).")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> UserContext:
    """Verify the Bearer token and return the authenticated :class:`UserContext`."""
    try:
        return decode_token(credentials.credentials)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid or expired token"},
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


__all__ = ["get_current_user"]
