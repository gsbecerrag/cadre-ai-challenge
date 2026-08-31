"""The Triage Agent's trigger: a Firebase Function (Python gen2) on Feedback writes.

Deliberately thin. Everything the agent does is `core.triage.triage_feedback`, which takes its
seams as arguments and is tested at seam S3 with a fake event, the in-memory store and the stub
provider. What is here is the part that only exists because Firestore is how the work arrives:
the decorator, the decode of the event, and the production seams built from the environment.
That boundary is ADR-0005's, and it is what would let the fallback trigger — a background task
in the API, if the Functions deploy is ever blocked — call exactly the same handler.

**Writes, not creations.** Ticket 12 made a changed thumb an update to the one Feedback
document rather than a second document, so a Visitor who presses 👍 and then 👎 produces an
update and no creation at all. `on_document_written` sees both; the handler decides, and it
decides on one field — `rating == "down"` — so a thumbs-up never reaches the model.

**The core package is copied in at deploy time** by `make deploy-functions` (`core/` and
`knowledge/` are rsynced into this directory and are gitignored here). Nothing is rendered or
generated: the copy is the same source the API runs, which is what keeps the triage prompt
byte-identical to the chat prompt and therefore on the same warm cache.

Local: `make deploy-functions COPY_ONLY=1`, then `firebase emulators:start --only
functions,firestore` and a written `feedback/{trace_id}` document with `rating: "down"` — the
flow is in functions/README.md, and `scripts/write-feedback.py` is the write.
"""

import asyncio
from typing import Any

from firebase_functions import firestore_fn, options

from core.adapters.firestore_store import FirestoreConversationStore
from core.adapters.knowledge_files import FileKnowledgeSource
from core.adapters.openrouter_provider import OpenRouterModelProvider
from core.config import Settings
from core.knowledge import compile_knowledge_base, render_knowledge_block
from core.logging import configure_logging, get_logger
from core.store import ConversationStore
from core.tracing import NoopTracer, TraceBoundary, Tracer
from core.triage import triage_feedback

# The Firestore trigger has to live where the database does, and both the database and the
# Cloud Run service are in this region.
REGION = "us-central1"

# Bound from Secret Manager by the Firebase CLI, and granted to the runtime service account by
# `make deploy-secrets`. Without the OpenRouter key there is no report; without the Langfuse
# keys the report is written and the Trace simply does not carry its summary.
SECRETS = ["OPENROUTER_API_KEY", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"]

# One report is one model call over the whole Knowledge Base: seconds, not milliseconds. The
# instance cap is a spend guard — a bug that wrote a thousand Feedback documents would
# otherwise be a thousand Sonnet 5 calls before anybody noticed.
TIMEOUT_SECONDS = 180
MAX_INSTANCES = 5

logger = get_logger("functions.triage")

# Built on the first event and kept for the life of the instance: the Knowledge Base is
# compiled once (it is ~25K tokens of cached prompt prefix, and recompiling it per event would
# be both wasted work and a chance to differ from the API's copy), and the Firestore client's
# gRPC channel belongs to the loop that will use it. Lazy rather than at import, because the
# Firebase CLI imports this module to discover the functions in it — during a deploy, on a
# laptop, with no secrets bound — and a missing key must not fail that discovery.
_agent: dict[str, Any] = {}


def _tracer(settings: Settings) -> Tracer:
    """Langfuse when both keys are bound, and nothing at all otherwise. A Trace that does not
    carry the triage summary is a small loss; a Triage Agent that will not start because an
    observability vendor is unreachable is a large one."""
    if not (settings.langfuse_public_key.strip() and settings.langfuse_secret_key.strip()):
        logger.info("Langfuse keys are not set; Triage Reports are written untraced")
        return NoopTracer()
    from core.adapters.langfuse_tracer import LangfuseTracer

    return TraceBoundary(
        LangfuseTracer(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
            environment=settings.env,
        )
    )


def _seams() -> dict[str, Any]:
    """The production seams, built once per instance and passed to the handler."""
    if not _agent:
        settings = Settings()
        configure_logging(level=settings.loglevel)
        store: ConversationStore = FirestoreConversationStore(project=settings.google_cloud_project)
        _agent.update(
            store=store,
            provider=OpenRouterModelProvider(
                api_key=settings.openrouter_api_key,
                model=settings.triage_model_id,
                app_url=settings.openrouter_app_url,
                app_name=settings.openrouter_app_name,
                cache_ttl=settings.prompt_cache_ttl,
                base_url=settings.openrouter_base_url,
            ),
            tracer=_tracer(settings),
            knowledge=render_knowledge_block(
                compile_knowledge_base(FileKnowledgeSource().documents())
            ),
            model=settings.triage_model_id,
        )
        logger.info("The Triage Agent is ready", extra={"model": settings.triage_model_id})
    return _agent


@firestore_fn.on_document_written(
    document="feedback/{feedback_id}",
    region=REGION,
    secrets=SECRETS,
    memory=options.MemoryOption.MB_512,
    timeout_sec=TIMEOUT_SECONDS,
    max_instances=MAX_INSTANCES,
)
def triage_on_feedback_written(
    event: firestore_fn.Event[firestore_fn.Change[firestore_fn.DocumentSnapshot | None]],
) -> None:
    """Triage the Feedback this event delivered, if it is a thumbs-down.

    The document as it stands after the write is the whole input: a deletion (no `after`) is
    nothing to triage, and every other decision — up or down, changed or not — belongs to the
    handler, where it is tested. Exceptions are swallowed on purpose: Firestore triggers are
    at-least-once and this one is registered without retries, so a raised exception would buy
    a red line in the console and nothing else, while a Visitor's Turn has long since ended.
    """
    after = event.data.after if event.data is not None else None
    if after is None:
        return
    try:
        asyncio.run(triage_feedback(after.to_dict() or {}, **_seams()))
    except Exception:
        logger.exception("The Triage Agent could not finish a Feedback event")
