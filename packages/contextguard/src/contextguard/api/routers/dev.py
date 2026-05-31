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

_DEFAULT_OLLAMA_URL = "http://localhost:11434"
_DEFAULT_CHAT_MODEL = "qwen2.5:7b"
# Pulling a model downloads gigabytes; give Ollama a generous blocking window.
_PULL_TIMEOUT_SECONDS = 1800.0



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


class DevModel(BaseModel):
    """One chat model installed in the local Ollama, with its disk size."""

    name: str
    size_bytes: int = Field(0, description="On-disk size in bytes (0 if unknown).")


class DevModelsResponse(BaseModel):
    """The installed chat models and which one the query path is using now."""

    active: str
    models: list[DevModel]


class DevSetModelRequest(BaseModel):
    """Which installed model the query path should use from now on."""

    model: str = Field(..., min_length=1, description="An installed Ollama model name.")


class DevSetModelResponse(BaseModel):
    """Confirmation that the live chat model was switched."""

    model: str


class DevPullModelRequest(BaseModel):
    """Which model to download into the local Ollama."""

    model: str = Field(..., min_length=1, description="Ollama model name, e.g. 'qwen2.5:7b'.")


class DevPullModelResponse(BaseModel):
    """Result of a (blocking) model pull."""

    model: str
    status: str



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


def _ollama_base_url() -> str:
    return (os.getenv("OLLAMA_BASE_URL") or _DEFAULT_OLLAMA_URL).rstrip("/")


def _active_model() -> str:
    return os.getenv("OLLAMA_CHAT_MODEL") or _DEFAULT_CHAT_MODEL


def _require_dev_enabled() -> None:
    if not _dev_minting_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "dev tools are disabled (JWT_SECRET is configured)"},
        )


def _installed_models() -> list[DevModel]:
    """Ask the local Ollama which chat models are pulled (GET /api/tags)."""
    import httpx

    try:
        resp = httpx.get(f"{_ollama_base_url()}/api/tags", timeout=10.0)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": f"cannot reach Ollama at {_ollama_base_url()}", "cause": str(exc)},
        ) from exc

    models = resp.json().get("models", [])
    return [
        DevModel(name=entry["name"], size_bytes=int(entry.get("size", 0)))
        for entry in models
        if entry.get("name")
    ]


@router.get("/v1/dev/models", response_model=DevModelsResponse)
def list_models() -> DevModelsResponse:
    """List the chat models installed in the local Ollama and the active one."""
    _require_dev_enabled()
    return DevModelsResponse(active=_active_model(), models=_installed_models())


@router.post("/v1/dev/model", response_model=DevSetModelResponse)
def set_model(request: DevSetModelRequest) -> DevSetModelResponse:
    """Switch the model used by the live query path (dev only).

    The gateway resolves ``OLLAMA_CHAT_MODEL`` on every call, so writing the env
    var here re-points the already-cached gateway without a restart.
    """
    _require_dev_enabled()

    installed = {model.name for model in _installed_models()}
    if request.model not in installed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": f"model {request.model!r} is not installed",
                "hint": "pull it first via POST /v1/dev/models/pull",
            },
        )

    os.environ["OLLAMA_CHAT_MODEL"] = request.model
    return DevSetModelResponse(model=request.model)


@router.post("/v1/dev/models/pull", response_model=DevPullModelResponse)
def pull_model(request: DevPullModelRequest) -> DevPullModelResponse:
    """Download a model into the local Ollama (blocking, dev only)."""
    _require_dev_enabled()

    import httpx

    try:
        resp = httpx.post(
            f"{_ollama_base_url()}/api/pull",
            json={"model": request.model, "stream": False},
            timeout=_PULL_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": f"pull of {request.model!r} failed", "cause": str(exc)},
        ) from exc

    return DevPullModelResponse(model=request.model, status=str(resp.json().get("status", "ok")))


__all__ = ["router"]
