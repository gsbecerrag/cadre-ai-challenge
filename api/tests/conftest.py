"""Fixtures for the HTTP tests (seam S1): a test client over a stand-in built web app."""

import io
import json
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from core.config import Settings
from core.logging import configure_logging

INDEX_HTML = "<!doctype html><title>Cadre AI</title><div id='root'></div>"
BUNDLE_JS = "console.log('cadre');"

LogReader = Callable[[], list[dict[str, Any]]]


@pytest.fixture
def web_dist(tmp_path: Path) -> Path:
    """A stand-in for `web/dist`, so the HTTP tests never depend on a Vite build."""
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (dist / "assets" / "index.js").write_text(BUNDLE_JS, encoding="utf-8")
    return dist


@pytest.fixture
def settings() -> Settings:
    return Settings(env="production", loglevel="INFO", app_version="0.1.0")


@pytest.fixture
def client(settings: Settings, web_dist: Path) -> Iterator[TestClient]:
    with TestClient(create_app(settings=settings, web_dist=web_dist)) as test_client:
        yield test_client


@pytest.fixture
def captured_logs(client: TestClient) -> LogReader:
    """Redirects the app's JSON log lines into a buffer the test can read back."""
    stream = io.StringIO()
    configure_logging(level="INFO", stream=stream)
    return lambda: [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]
