"""``POST /v1/dev/token`` - mint a demo identity token from the browser (dev only).

The dashboard needs a *valid, unexpired* token to exercise the secured
``/v1/query`` path. Copy-pasting the output of ``make token`` works but expires
after an hour and is clumsy in a demo. This endpoint mints the same signed JWT
that ``scripts/issue_token.py`` does, for any demo identity in
``data/users.yaml``, so the UI can offer a one-click "Generate token" button.

Strictly dev/demo (ADR-015): it is a deliberate auth-minting shortcut and is
**disabled automatically whenever a real ``JWT_SECRET`` is configured** (i.e. any
non-dev deployment). With a real signing secret set, the endpoint returns 403 and
mints nothing - tokens must then come from the IdP / ``make token`` operator flow.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml
from contextguard_contracts import UserContext
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from contextguard.auth import DEFAULT_TTL_SECONDS, issue_token

router = APIRouter(tags=["dev"])

# Default location of the demo identities, overridable for tests / alt layouts.
_USERS_PATH = Path(os.getenv("USERS_PATH", "data/users.yaml"))


class DevTokenRequest(BaseModel):
    """Which demo identity to mint a token for."""

    sub: str = Field(..., min_length=1, description="Demo identity 'sub' from data/users.yaml.")


class DevIdentity(BaseModel):
    """A demo identity the dev minter can issue a token for."""

    sub: str
    tenant: str
    role: str
    purpose: str


class DevTokenResponse(BaseModel):
    """A freshly minted demo token and the identity it carries."""

    token: str
    sub: str
    tenant: str
    role: str
    purpose: str
    expires_in: int


@lru_cache(maxsize=1)
def _load_identities() -> dict[str, UserContext]:
    raw = yaml.safe_load(_USERS_PATH.read_text(encoding="utf-8")) or {}
    return {entry["sub"]: UserContext(**entry) for entry in raw.get("users", [])}


def _dev_minting_enabled() -> bool:
    """Dev minting is on only while the dev fallback secret is in use."""
    return not os.getenv("JWT_SECRET")


@router.get("/v1/dev/identities", response_model=list[DevIdentity])
def list_identities() -> list[DevIdentity]:
    """List the demo identities the dev minter can issue tokens for."""
    if not _dev_minting_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "dev token minting is disabled (JWT_SECRET is configured)"},
        )
    return [DevIdentity(**user.model_dump()) for user in _load_identities().values()]


@router.post("/v1/dev/token", response_model=DevTokenResponse)
def mint_token(request: DevTokenRequest) -> DevTokenResponse:
    """Mint a signed token for a demo identity (dev only)."""
    if not _dev_minting_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "dev token minting is disabled (JWT_SECRET is configured)"},
        )

    user = _load_identities().get(request.sub)
    if user is None:
        known = ", ".join(sorted(_load_identities())) or "(none)"
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": f"unknown identity {request.sub!r}", "known": known},
        )

    return DevTokenResponse(
        token=issue_token(user),
        sub=user.sub,
        tenant=user.tenant,
        role=user.role,
        purpose=user.purpose,
        expires_in=DEFAULT_TTL_SECONDS,
    )


__all__ = ["router"]
