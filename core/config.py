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
ModelProviderName = Literal["stub", "openrouter"]
ConversationStoreName = Literal["memory", "firestore"]
CacheTtl = Literal["5m", "1h"]

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
    # Which implementation sits behind the `ModelProvider` seam. `stub` costs nothing and
    # needs no key, which is what CI, the load smoke test and a local demo run on.
    model_provider: ModelProviderName = "stub"
    # Which implementation sits behind the `ConversationStore` seam. `memory` is process-local
    # and therefore wrong for a service that scales past one instance; Cloud Run gets
    # `firestore`.
    conversation_store: ConversationStoreName = "memory"

    # --- OpenRouter (ADR-0002: the only runtime model provider) ---
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    chat_model: str = "anthropic/claude-sonnet-5"
    # How long OpenRouter asks the upstream to keep the cached system block. The Knowledge
    # Base is the whole prefix (ADR-0001), so an hour is the difference between paying full
    # input price on every Turn and paying a tenth of it.
    prompt_cache_ttl: CacheTtl = "1h"
    # Attribution, so OpenRouter's dashboard shows the spend under this app.
    openrouter_app_url: str = ""
    openrouter_app_name: str = "Cadre AI Support Agent"

    # --- Sessions ---
    # Signs the Session cookie. Blank is tolerated in development (a per-process key is
    # generated) and fatal in production, where a guessable Session id would be a way into
    # someone else's conversation.
    session_cookie_secret: str = ""
    # A burst guard: past this many Turns a Session is closed politely with the contact path.
    max_turns_per_session: int = 40

    # --- GCP ---
    # Firestore reads this when it is set; on Cloud Run the metadata server supplies it.
    google_cloud_project: str = ""


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
