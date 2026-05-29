"""Core tier: app factory builds without any network/infra."""

from __future__ import annotations

from fastapi import FastAPI

from contextguard.api.app import create_app


def test_create_app_returns_fastapi() -> None:
    app = create_app()
    assert isinstance(app, FastAPI)
    assert app.title == "ContextGuard"
