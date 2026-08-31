"""Typed runtime configuration, read from the environment.

`.env.example` at the repository root is the schema. Nothing here reads a dotenv file:
the container gets real environment variables (secrets from Secret Manager) and `make dev`
passes `--env-file .env` to `uv run`, so tests and the container never pick up a stray `.env`.
"""

import os
from collections.abc import Mapping, Sequence
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Variables that must be present before the app may start. Only the variables the selected
# providers actually need belong here; the scaffold selects none, so it is empty. Later
# tickets add their provider's keys and a missing one then fails fast at startup.
REQUIRED_VARIABLES: tuple[str, ...] = ()


class MissingConfigurationError(RuntimeError):
    """Raised at startup when a required environment variable is absent or blank."""


class Settings(BaseSettings):
    """Everything the process needs to run, with a default for everything non-secret."""

    model_config = SettingsConfigDict(env_file=None, extra="ignore", frozen=True)

    env: Environment = "development"
    port: int = 8080
    loglevel: LogLevel = "INFO"
    service_name: str = "cadre-support-agent"
    app_version: str = "0.1.0"


def load_settings(
    required: Sequence[str] = REQUIRED_VARIABLES,
    environ: Mapping[str, str] | None = None,
) -> Settings:
    """Validate that the required variables are set, then build the typed settings."""
    present = os.environ if environ is None else environ
    missing = [name for name in required if not present.get(name, "").strip()]
    if missing:
        raise MissingConfigurationError(
            "Missing required configuration: "
            + ", ".join(missing)
            + ". Set it in the environment (see .env.example)."
        )
    return Settings()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """The process-wide settings, loaded once."""
    return load_settings()
