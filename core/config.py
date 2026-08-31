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

from core.qualification import DEFAULT_QUALIFICATION_THRESHOLD

Environment = Literal["development", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
ModelProviderName = Literal["stub", "openrouter"]
ConversationStoreName = Literal["memory", "firestore"]
ConsoleAuthName = Literal["firebase", "fake"]
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
    # What the Triage Agent asks (ADR-0005). Blank means "the conversation model", which is
    # the point: the triage call reuses the chat prompt's cached prefix, and a different model
    # would read the same 25K tokens off a cache it cannot share. It is configuration anyway,
    # so a cheaper model can be tried on the Triage Agent alone without touching a Turn.
    triage_model: str = ""

    # --- Sessions ---
    # Signs the Session cookie. Blank is tolerated in development (a per-process key is
    # generated) and fatal in production, where a guessable Session id would be a way into
    # someone else's conversation.
    session_cookie_secret: str = ""
    # A burst guard: past this many Turns a Session is closed politely with the contact path.
    max_turns_per_session: int = 40

    # --- Leads ---
    # The Qualification Score at which a Lead becomes a Qualified Lead and the Hand-over offer
    # is unlocked (ADR-0009). It lives here rather than in the prompt because it is a business
    # decision a Strategist may want to move without a deploy of new wording.
    qualification_threshold: int = DEFAULT_QUALIFICATION_THRESHOLD

    # --- Hand-over (ADR-0007) ---
    # Whether an accepted Hand-over may become a video call at all. Off by default and off on
    # the deployed service until the Daily.co room exists (ticket 15): with it off the
    # Assistant still offers the Hand-over and still captures the Lead — every acceptance is
    # simply a Callback. That is the point of the flag, and why it is not a secret: a video
    # outage must never block lead capture.
    live_handover_enabled: bool = False

    # --- Observability (Langfuse) ---
    # Both keys present turns tracing on; either one missing leaves it off, which is the
    # default for CI, `make dev` and every reviewer's laptop. A missing key is never a
    # startup failure: a Turn that cannot be traced is still a Turn that can be answered.
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    # The region the Langfuse project lives in. `us.` and `cloud.` are different data
    # residencies, and pointing at the wrong one is an authentication error, not a redirect.
    langfuse_host: str = "https://us.cloud.langfuse.com"

    # --- GCP ---
    # Firestore reads this when it is set; on Cloud Run the metadata server supplies it.
    google_cloud_project: str = ""

    # --- Strategist Console (ADR-0010) ---
    # The whole authorisation model: the emails allowed to open the Console, comma-separated.
    # Blank admits nobody — a deploy that forgets this closes the Console rather than
    # publishing every Lead's Contact Details.
    admin_allowed_emails: str = ""
    # Which implementation sits behind the `TokenVerifier` seam. `fake` decodes `fake:<email>`
    # so the Console can be demonstrated without Google sign-in, and is refused outside
    # development (see `build_token_verifier` in api/main.py).
    console_auth: ConsoleAuthName = "firebase"
    # The audience a Firebase ID token must carry. Blank falls back to GOOGLE_CLOUD_PROJECT,
    # which is the same project here; it is separate because Firebase Auth and Firestore do
    # not have to live in one project, and a token verified against the wrong audience is a
    # token from another app's users.
    firebase_project_id: str = ""

    @property
    def triage_model_id(self) -> str:
        """The model the Triage Agent calls: its own, or the conversation model."""
        return self.triage_model.strip() or self.chat_model

    @property
    def firebase_audience(self) -> str:
        """The Firebase project whose ID tokens this deployment accepts."""
        return self.firebase_project_id.strip() or self.google_cloud_project.strip()


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
