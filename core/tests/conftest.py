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
)


@pytest.fixture
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[pytest.MonkeyPatch]:
    for name in SETTINGS_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    yield monkeypatch
