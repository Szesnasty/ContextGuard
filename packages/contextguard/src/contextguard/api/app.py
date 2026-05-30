"""FastAPI application factory.

Kept deliberately thin: the HTTP layer is an adapter (ADR-004). Business logic
belongs in `contextguard.core`, not here.
"""

from __future__ import annotations

from fastapi import FastAPI

from contextguard import __version__


def create_app() -> FastAPI:
    """Build and return the ContextGuard FastAPI app."""
    app = FastAPI(
        title="ContextGuard",
        version=__version__,
        summary="Policy-aware context firewall for production RAG.",
    )

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    from contextguard.api.routers.query import router as query_router

    app.include_router(query_router)

    return app
