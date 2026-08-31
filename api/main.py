"""Composition root: build the FastAPI application the container runs.

Every seam is resolved here and nowhere else — the `ModelProvider`, the `ConversationStore`,
the `KnowledgeSource` — so a test builds the same application with the stub provider and the
in-memory store by passing them in.

Routes are registered before the web app is mounted at `/`, so the API always wins over the
single-page fallback.
"""

import secrets
from datetime import UTC, date, datetime
from pathlib import Path

from fastapi import FastAPI

from api.chat import create_chat_router
from api.console import create_console_router
from api.health import create_health_router
from api.knowledge import create_knowledge_router
from api.middleware import RequestContextMiddleware
from api.web import mount_web_app
from core.adapters.fake_verifier import DevTokenVerifier
from core.adapters.knowledge_files import FileKnowledgeSource
from core.adapters.memory_store import InMemoryConversationStore
from core.adapters.openrouter_provider import OpenRouterModelProvider
from core.adapters.stub_demo_script import demo_fallback, demo_scripts
from core.adapters.stub_provider import StubModelProvider
from core.auth import ClosedTokenVerifier, TokenVerifier, parse_allowlist
from core.config import MissingConfigurationError, Settings, load_settings
from core.knowledge import KnowledgeSource, compile_knowledge_base, render_knowledge_block
from core.logging import configure_logging, get_logger
from core.prompt import SystemPrompt, build_system_prompt
from core.provider import ModelProvider
from core.store import ConversationStore
from core.tools import default_tools
from core.turn import TurnRunner

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WEB_DIST = REPO_ROOT / "web" / "dist"

# Slow enough that a reviewer can watch an answer arrive, fast enough not to be annoying.
DEMO_DELAY_SECONDS = 0.05

logger = get_logger("app")


def resolve_cookie_secret(settings: Settings) -> str:
    """The key the Session cookie is signed with, or a refusal to start without one."""
    secret = settings.session_cookie_secret.strip()
    if secret:
        return secret
    if settings.env == "production":
        raise MissingConfigurationError(
            "SESSION_COOKIE_SECRET is not set. It signs the Session cookie, and without it a "
            "Session id is guessable — which is a way into somebody else's conversation. "
            "Generate one with `openssl rand -hex 32` (see .env.example)."
        )
    # Development convenience only: a key for this process. Sessions then do not survive a
    # restart, which is the honest behaviour for a machine that has configured no secret.
    logger.warning("SESSION_COOKIE_SECRET is not set; signing Sessions with a per-process key")
    return secrets.token_urlsafe(32)


def build_provider(settings: Settings) -> ModelProvider:
    """The `ModelProvider` seam. `stub` spends nothing and needs no key, which is what CI and
    a local demo run on; `openrouter` is the one production implementation (ADR-0002)."""
    if settings.model_provider == "stub":
        return StubModelProvider(
            scripts=demo_scripts(),
            fallback=demo_fallback(),
            delay_seconds=DEMO_DELAY_SECONDS,
        )
    if not settings.openrouter_api_key.strip():
        raise MissingConfigurationError(
            "MODEL_PROVIDER=openrouter needs OPENROUTER_API_KEY. On Cloud Run it is bound "
            "from Secret Manager by `make deploy`; locally it comes from .env "
            "(see .env.example). Set MODEL_PROVIDER=stub to run without a key."
        )
    return OpenRouterModelProvider(
        api_key=settings.openrouter_api_key,
        model=settings.chat_model,
        app_url=settings.openrouter_app_url,
        app_name=settings.openrouter_app_name,
        cache_ttl=settings.prompt_cache_ttl,
        base_url=settings.openrouter_base_url,
    )


def build_store(settings: Settings) -> ConversationStore:
    """The `ConversationStore` seam. In memory a Session lives in one process, which is wrong
    for a service that scales past one instance — Cloud Run selects `firestore`."""
    if settings.conversation_store == "memory":
        return InMemoryConversationStore()
    # Imported here, not at the top: the Firestore client drags in gRPC and protobuf, and a
    # container running the in-memory store should not pay for that on a cold start.
    from core.adapters.firestore_store import FirestoreConversationStore

    return FirestoreConversationStore(project=settings.google_cloud_project)


def build_token_verifier(settings: Settings, allowlist: frozenset[str]) -> TokenVerifier:
    """The `TokenVerifier` seam: who the Console believes a request comes from (ADR-0010).

    An empty allowlist means this deployment has no Console — nobody could be admitted even
    with a perfectly valid token — so it gets the closed verifier rather than a demand for a
    Firebase project. That is what keeps CI, the unit tests and a bare `make dev` from needing
    one.

    `fake` is a demonstration mode: it turns `fake:<email>` into a Strategist, so the Console
    can be opened and clicked through without a Google Workspace account. It accepts an
    identity anyone can type, so selecting it outside development is a startup failure rather
    than a surprising one at the first request.
    """
    if not allowlist:
        return ClosedTokenVerifier()
    if settings.console_auth == "fake":
        if settings.env != "development":
            raise MissingConfigurationError(
                "CONSOLE_AUTH=fake accepts any identity a caller types and is refused when "
                f"ENV={settings.env}. The Console shows every Lead's Contact Details, so the "
                "deployed service must verify real Firebase ID tokens (CONSOLE_AUTH=firebase)."
            )
        logger.warning(
            "CONSOLE_AUTH=fake: the Console accepts fake:<email> credentials without Google"
        )
        return DevTokenVerifier()
    # Imported here, not at the top: `google-auth`'s transport is only needed by a deployment
    # that actually verifies tokens, and the demo mode should not pay for the import.
    from core.adapters.firebase_verifier import FirebaseTokenVerifier

    if not settings.firebase_audience:
        raise MissingConfigurationError(
            "CONSOLE_AUTH=firebase needs the Firebase project whose ID tokens it accepts. "
            "Set GOOGLE_CLOUD_PROJECT (or FIREBASE_PROJECT_ID) — a token verified against no "
            "audience is a token from any Firebase project's users (see .env.example)."
        )
    return FirebaseTokenVerifier(project_id=settings.firebase_audience)


def create_app(
    settings: Settings | None = None,
    web_dist: Path | None = None,
    provider: ModelProvider | None = None,
    store: ConversationStore | None = None,
    knowledge: KnowledgeSource | None = None,
    verifier: TokenVerifier | None = None,
) -> FastAPI:
    """Wire the application. A missing required variable fails fast here, before serving."""
    resolved = load_settings() if settings is None else settings
    configure_logging(level=resolved.loglevel)
    cookie_secret = resolve_cookie_secret(resolved)

    # The Knowledge Base is compiled once, at startup: it is the cached prefix of every
    # prompt, and recompiling it per Turn would be both wasted work and a chance to differ.
    source = knowledge if knowledge is not None else FileKnowledgeSource()
    sections = compile_knowledge_base(source.documents())
    if not sections:
        # An empty Knowledge Base is silent: the prompt assembles, the Assistant starts, and
        # every answer is ungrounded. This is what a container built without `knowledge/`
        # looks like, so it has to be a startup failure rather than a runtime surprise.
        raise MissingConfigurationError(
            f"The Knowledge Base compiled to no KB Sections from {source.location}. "
            "The Assistant may only state what a KB Section states, so it cannot start."
        )
    knowledge_block = render_knowledge_block(sections)

    def build_prompt() -> SystemPrompt:
        return build_system_prompt(knowledge_block, today=_today())

    # One store instance, not two: the Turn's history and the Session's Lead are written to
    # the same database, and `capture_lead` reaches it through the tool registry.
    conversation_store = store if store is not None else build_store(resolved)
    runner = TurnRunner(
        provider=provider if provider is not None else build_provider(resolved),
        store=conversation_store,
        tools=default_tools(
            conversation_store, qualification_threshold=resolved.qualification_threshold
        ),
        build_prompt=build_prompt,
        max_turns=resolved.max_turns_per_session,
    )

    app = FastAPI(title="Cadre AI Support Agent", version=resolved.app_version)
    app.state.settings = resolved
    app.add_middleware(RequestContextMiddleware)
    app.include_router(create_health_router(resolved))
    # Google's frontend answers `/healthz` on *.run.app itself and the request never reaches
    # the container, so the deployed service is probed under the API prefix instead.
    app.include_router(create_health_router(resolved), prefix="/api")
    app.include_router(
        create_chat_router(
            runner,
            cookie_secret=cookie_secret,
            secure_cookie=resolved.env == "production",
        ),
        prefix="/api",
    )
    app.include_router(create_knowledge_router(sections), prefix="/api")
    # The allowlist is parsed once, here, and the same environment variable renders
    # `firestore.rules` (`make rules`) — the two enforcement points ADR-0010 accepted have one
    # source, even though they cannot share a runtime.
    allowlist = parse_allowlist(resolved.admin_allowed_emails)
    if not allowlist:
        logger.warning("ADMIN_ALLOWED_EMAILS is not set; the Console will admit nobody")
    app.include_router(
        create_console_router(
            conversation_store,
            verifier=(
                verifier if verifier is not None else build_token_verifier(resolved, allowlist)
            ),
            allowlist=allowlist,
        ),
        prefix="/api",
    )
    mount_web_app(app, DEFAULT_WEB_DIST if web_dist is None else web_dist)
    return app


def _today() -> date:
    """UTC, so the only volatile line in the prompt does not depend on where this runs."""
    return datetime.now(tz=UTC).date()


app = create_app()
