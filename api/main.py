"""Composition root: build the FastAPI application the container runs.

Every seam is resolved here and nowhere else — the `ModelProvider`, the `ConversationStore`,
the `KnowledgeSource` — so a test builds the same application with the stub provider and the
in-memory store by passing them in.

Routes are registered before the web app is mounted at `/`, so the API always wins over the
single-page fallback.
"""

from datetime import UTC, date, datetime
from pathlib import Path

from fastapi import FastAPI

from api.chat import create_chat_router
from api.health import create_health_router
from api.knowledge import create_knowledge_router
from api.middleware import RequestContextMiddleware
from api.web import mount_web_app
from core.adapters.knowledge_files import FileKnowledgeSource
from core.adapters.memory_store import InMemoryConversationStore
from core.adapters.stub_demo_script import demo_fallback, demo_scripts
from core.adapters.stub_provider import StubModelProvider
from core.config import MissingConfigurationError, Settings, load_settings
from core.knowledge import KnowledgeSource, compile_knowledge_base, render_knowledge_block
from core.logging import configure_logging
from core.prompt import SystemPrompt, build_system_prompt
from core.provider import ModelProvider
from core.store import ConversationStore
from core.tools import default_tools
from core.turn import TurnRunner

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WEB_DIST = REPO_ROOT / "web" / "dist"

# Slow enough that a reviewer can watch an answer arrive, fast enough not to be annoying.
DEMO_DELAY_SECONDS = 0.05


def build_provider(settings: Settings) -> ModelProvider:
    if settings.model_provider == "stub":
        return StubModelProvider(
            scripts=demo_scripts(),
            fallback=demo_fallback(),
            delay_seconds=DEMO_DELAY_SECONDS,
        )
    raise MissingConfigurationError(
        "MODEL_PROVIDER=openrouter has no implementation yet — it arrives with ticket 03. "
        "Set MODEL_PROVIDER=stub to run the Assistant against the scripted provider."
    )


def create_app(
    settings: Settings | None = None,
    web_dist: Path | None = None,
    provider: ModelProvider | None = None,
    store: ConversationStore | None = None,
    knowledge: KnowledgeSource | None = None,
) -> FastAPI:
    """Wire the application. A missing required variable fails fast here, before serving."""
    resolved = load_settings() if settings is None else settings
    configure_logging(level=resolved.loglevel)

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

    runner = TurnRunner(
        provider=provider if provider is not None else build_provider(resolved),
        store=store if store is not None else InMemoryConversationStore(),
        tools=default_tools(),
        build_prompt=build_prompt,
    )

    app = FastAPI(title="Cadre AI Support Agent", version=resolved.app_version)
    app.state.settings = resolved
    app.add_middleware(RequestContextMiddleware)
    app.include_router(create_health_router(resolved))
    # Google's frontend answers `/healthz` on *.run.app itself and the request never reaches
    # the container, so the deployed service is probed under the API prefix instead.
    app.include_router(create_health_router(resolved), prefix="/api")
    app.include_router(
        create_chat_router(runner, secure_cookie=resolved.env == "production"),
        prefix="/api",
    )
    app.include_router(create_knowledge_router(sections), prefix="/api")
    mount_web_app(app, DEFAULT_WEB_DIST if web_dist is None else web_dist)
    return app


def _today() -> date:
    """UTC, so the only volatile line in the prompt does not depend on where this runs."""
    return datetime.now(tz=UTC).date()


app = create_app()
