"""Fixtures shared by the core unit tests (seam S2)."""

from collections.abc import Iterator

import pytest

# Every environment variable the Settings model reads. Cleared so a unit test sees the
# documented defaults rather than whatever the developer's shell happens to export.
SETTINGS_VARIABLES = (
    "ENV",
    "PORT",
    "LOGLEVEL",
    "APP_VERSION",
    "SERVICE_NAME",
    "MODEL_PROVIDER",
    "CONVERSATION_STORE",
    "OPENROUTER_API_KEY",
    "OPENROUTER_BASE_URL",
    "CHAT_MODEL",
    "PROMPT_CACHE_TTL",
    "OPENROUTER_APP_URL",
    "OPENROUTER_APP_NAME",
    "SESSION_COOKIE_SECRET",
    "MAX_TURNS_PER_SESSION",
    "GOOGLE_CLOUD_PROJECT",
)


@pytest.fixture
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[pytest.MonkeyPatch]:
    for name in SETTINGS_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    yield monkeypatch
