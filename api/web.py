"""Serve the built web app from the same origin as the API (ADR-0003: one container, one URL)."""

from pathlib import Path

from fastapi import FastAPI
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

INDEX_FILE = "index.html"
ASSETS_PREFIX = "assets/"


class SinglePageApp(StaticFiles):
    """Static files, with client-side routes falling back to the app shell."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except HTTPException as missing:
            # A missing hashed bundle stays a 404 — answering it with HTML would make a
            # broken build look like a working page.
            if missing.status_code == 404 and not path.startswith(ASSETS_PREFIX):
                return await super().get_response(INDEX_FILE, scope)
            raise


def mount_web_app(app: FastAPI, web_dist: Path) -> None:
    """Mount `web/dist` at the root, if it has been built (`make dev` serves it from Vite)."""
    if not (web_dist / INDEX_FILE).is_file():
        return
    app.mount("/", SinglePageApp(directory=web_dist, html=True), name="web")
