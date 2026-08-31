"""Composition root: build the FastAPI application the container runs.

Routes are registered before the web app is mounted at `/`, so the API always wins over the
single-page fallback.
"""

from pathlib import Path

from fastapi import FastAPI

from api.health import create_health_router
from api.middleware import RequestContextMiddleware
from api.web import mount_web_app
from core.config import Settings, load_settings
from core.logging import configure_logging

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WEB_DIST = REPO_ROOT / "web" / "dist"


def create_app(settings: Settings | None = None, web_dist: Path | None = None) -> FastAPI:
    """Wire the application. A missing required variable fails fast here, before serving."""
    resolved = load_settings() if settings is None else settings
    configure_logging(level=resolved.loglevel)

    app = FastAPI(title="Cadre AI Support Agent", version=resolved.app_version)
    app.state.settings = resolved
    app.add_middleware(RequestContextMiddleware)
    app.include_router(create_health_router(resolved))
    # Google's frontend answers `/healthz` on *.run.app itself and the request never reaches
    # the container, so the deployed service is probed under the API prefix instead.
    app.include_router(create_health_router(resolved), prefix="/api")
    mount_web_app(app, DEFAULT_WEB_DIST if web_dist is None else web_dist)
    return app


app = create_app()
