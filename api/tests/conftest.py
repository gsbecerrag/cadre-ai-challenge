"""Fixtures for the HTTP tests (seam S1).

A test client over a stand-in built web app, the scriptable stub `ModelProvider` and the
in-memory `ConversationStore` — the two seams that keep a Turn off the network.
"""

import io
import json
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import httpx2
import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from core.adapters.memory_store import InMemoryConversationStore
from core.adapters.stub_provider import StubModelProvider
from core.config import Settings
from core.logging import configure_logging

INDEX_HTML = "<!doctype html><title>Cadre AI</title><div id='root'></div>"
# Obviously fake: the Session cookie's signing key for the HTTP tests.
COOKIE_SECRET = "test-session-cookie-secret-not-a-real-one"
BUNDLE_JS = "console.log('cadre');"
APP_LOGGER_PREFIX = "cadre."

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
    return Settings(
        env="production",
        loglevel="INFO",
        app_version="0.1.0",
        session_cookie_secret=COOKIE_SECRET,
    )


@pytest.fixture
def provider() -> StubModelProvider:
    """Scripted per test: given the last Visitor message it returns canned text, a tool call,
    a usage block, or a provider error."""
    return StubModelProvider()


@pytest.fixture
def store() -> InMemoryConversationStore:
    return InMemoryConversationStore()


@pytest.fixture
def client(
    settings: Settings,
    web_dist: Path,
    provider: StubModelProvider,
    store: InMemoryConversationStore,
) -> Iterator[TestClient]:
    app = create_app(settings=settings, web_dist=web_dist, provider=provider, store=store)
    # https, because the settings above are the production ones and the Session cookie is
    # then marked Secure — over http the client would silently drop it and every Turn would
    # look like a new Session, which is exactly the bug the cookie tests exist to catch.
    with TestClient(app, base_url="https://testserver") as test_client:
        yield test_client


def sse_events(response: httpx2.Response) -> list[tuple[str, dict[str, Any]]]:
    """The `(name, payload)` pairs a browser's EventSource parser would see."""
    events: list[tuple[str, dict[str, Any]]] = []
    for frame in response.text.split("\n\n"):
        if not frame.strip():
            continue
        name_line, data_line = frame.split("\n")
        events.append(
            (name_line.removeprefix("event: "), json.loads(data_line.removeprefix("data: ")))
        )
    return events


@pytest.fixture
def captured_logs(client: TestClient) -> LogReader:
    """The application's own JSON log lines, read back from a buffer.

    Third-party libraries log through the managed root logger too — the test client's own
    HTTP client narrates every request — so lines are filtered to our loggers by name.
    """
    stream = io.StringIO()
    configure_logging(level="INFO", stream=stream)

    def read() -> list[dict[str, Any]]:
        records = [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]
        return [record for record in records if record["logger"].startswith(APP_LOGGER_PREFIX)]

    return read
