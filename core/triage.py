"""The Triage Agent: one thumbs-down in, one Triage Report out (ADR-0005).

This is the whole agent. The Firebase Function in `functions/main.py` is a decorator, a decode
and a call: it exists because Firestore triggers are how the work is delivered, not because
anything about the work belongs to Firebase. Keeping the handler here — taking the store, the
provider, the tracer and the Knowledge Base as arguments — is what lets seam S3 run it with a
fake event, the in-memory store and the stub provider, and what would let the fallback trigger
(a background task in the API, if the Functions deploy is ever blocked) call the same code.

Three properties are the design:

- **A thumbs-up costs nothing.** The trigger fires on every Feedback write, and the handler
  returns before the model is reached unless the rating is `down`. Most Feedback is a thumb up
  or a note added to one, and a Sonnet 5 call over the whole Knowledge Base is 5-8 cents.
- **A redelivery overwrites.** The report is keyed by the Feedback id, which is the Trace id,
  so an at-least-once trigger delivered twice writes one document twice. There is no "have I
  already run" flag to read, and nothing to reconcile.
- **A model that answers badly is not an outage.** The call asks for strict JSON against a
  schema the provider enforces, and anything that comes back unparsable becomes a report in
  category `other` carrying the raw text. A Cadre engineer reads *something* either way, which
  is worth more than a crash in a log nobody is watching.

The prompt is the chat Assistant's own cached prefix, byte for byte, with the triage
instructions in the volatile tail — so this call lands on the prompt cache the conversation
just paid to write (ADR-0001, ADR-0005).
"""

import json
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from typing import Any

from core.logging import get_logger, session_context
from core.prompt import SystemPrompt, build_system_prompt, build_volatile_block
from core.provider import (
    ModelMessage,
    ModelProvider,
    ProviderError,
    ProviderRequest,
    TextDelta,
    Usage,
)
from core.store import (
    TRIAGE_CATEGORIES,
    TRIAGE_SEVERITIES,
    ConversationStore,
    Feedback,
    TriageCategory,
    TriageReport,
    TriageSeverity,
)
from core.tracing import Tracer

logger = get_logger("triage")

# What the Triage Agent's summary is called on the Trace it analysed. Deliberately not
# `FEEDBACK_SCORE_NAME`: Langfuse ingests scores by an id derived from the Trace and the name
# (core/adapters/langfuse_tracer.py), so writing the triage summary under the Feedback's name
# would overwrite the Visitor's own thumb with a severity. Two names, two scores, one Trace.
TRIAGE_SCORE_NAME = "triage"

# The severity as a number, because a Langfuse score is a number with a comment attached. The
# comment is the summary — the thing a Cadre engineer actually reads — and the value is what
# sorts and filters: 3 is the Turn to open first.
SEVERITY_SCORES: Mapping[TriageSeverity, float] = {"low": 1.0, "medium": 2.0, "high": 3.0}

# Where a report lands when the model could not place it, or could not be parsed at all.
FALLBACK_CATEGORY: TriageCategory = "other"
FALLBACK_SEVERITY: TriageSeverity = "medium"

# The name the schema travels under. OpenRouter passes it to the provider, and it is what a
# strict-mode rejection names, so it is worth being the report's own word.
SCHEMA_NAME = "triage_report"

# The two roles the Triage Agent reads. Tool traffic is not conversation: the Visitor never saw
# a `capture_lead` result, so it is not evidence of what they were unhappy with.
CONVERSATION_ROLES = ("visitor", "assistant")

TRIAGE_INSTRUCTIONS = """\
Stop answering Visitors. For this one request you are Cadre's Triage Agent: a Visitor pressed
thumbs-down on the exchange below, and you are writing the Triage Report a Cadre engineer
reads. Nothing you write here reaches a Visitor.

Judge the Assistant's answer against the Knowledge Base above — the only thing it was allowed
to state — and pick the one category that best explains the thumbs-down:

- kb_gap: the Knowledge Base carries no section that answers the question. The Assistant
  behaved correctly and Cadre is missing a published fact.
- wrong_escalation: the Knowledge Base did carry the answer and the Assistant escalated
  anyway, or it escalated to the wrong route.
- hallucination: the answer states something no KB Section carries, or cites a section that
  does not say it.
- tone: the facts were right and the answer read badly — lecturing, evasive, far too long, or
  in the wrong language.
- pii: personal data was asked for, repeated back, or handled in a way it should not be.
- bug: the product failed — a card that did not render, a broken route, a truncated answer.
- other: none of these describes it.

`summary` is two or three sentences a Strategist can read in a queue: what the Visitor wanted,
what they got, and why that earned a thumbs-down. `evidence` quotes the lines that show it —
the Visitor's words and the Assistant's, verbatim, never a paraphrase.
`suggested_kb_addition` names the KB Section id to add or change and says what it should
state; `suggested_eval_case` is one line in the shape of the evaluation suite: the Visitor
message, then the behaviour expected of the Assistant. Leave either empty when there is
nothing honest to suggest — an invented suggestion costs more to review than no suggestion.
`severity` is high when Cadre lost the conversation or published something untrue, medium when
a Visitor left without an answer they could have had, low when the answer was serviceable.

Answer with the JSON object the schema describes, and nothing else."""


def triage_response_format() -> dict[str, Any]:
    """The `response_format` the triage call carries: strict JSON against this schema.

    Every field is required and `additionalProperties` is false, which is what OpenRouter's
    strict structured outputs need (docs/research/openrouter-facts.md); "the model had no
    suggestion" is therefore an empty string rather than a missing key, which is also easier
    to render — the Console draws the box or it does not.
    """
    properties: dict[str, Any] = {
        "category": {
            "type": "string",
            "enum": list(TRIAGE_CATEGORIES),
            "description": "The one thing that best explains the thumbs-down.",
        },
        "summary": {
            "type": "string",
            "description": "Two or three sentences: what was wanted, what was given, why it "
            "earned a thumbs-down.",
        },
        "evidence": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Verbatim quotes from the conversation or the Visitor's comment.",
        },
        "suggested_kb_addition": {
            "type": "string",
            "description": "The KB Section id to add or change and what it should state. "
            "Empty when there is nothing honest to suggest.",
        },
        "suggested_eval_case": {
            "type": "string",
            "description": "One Eval Case: the Visitor message and the expected behaviour. "
            "Empty when there is nothing to add.",
        },
        "severity": {"type": "string", "enum": list(TRIAGE_SEVERITIES)},
    }
    return {
        "type": "json_schema",
        "json_schema": {
            "name": SCHEMA_NAME,
            "strict": True,
            "schema": {
                "type": "object",
                "properties": properties,
                "required": list(properties),
                "additionalProperties": False,
            },
        },
    }


def decode_feedback(document: Mapping[str, Any]) -> Feedback | None:
    """The Feedback a `feedback/{trace_id}` document records, or `None` if it is not one.

    Pure, and deliberately unforgiving: a deleted document arrives as empty fields, and a
    document whose rating is not a thumb is a schema this build does not understand. Either
    way there is nothing to triage, and guessing would mean spending a model call on it.
    """
    session_id = str(document.get("session_id") or "")
    trace_id = str(document.get("trace_id") or "")
    rating = str(document.get("rating") or "")
    if not session_id or not trace_id or rating not in ("up", "down"):
        return None
    return Feedback(
        session_id=session_id,
        trace_id=trace_id,
        rating="down" if rating == "down" else "up",
        comment=str(document.get("comment") or ""),
        changes=int(document.get("changes") or 0),
    )


def build_triage_prompt(knowledge: str, *, today: date) -> SystemPrompt:
    """The Assistant's own system prompt, with the triage instructions after the breakpoint.

    The cached half is byte-identical to a chat Turn's, which is the point: the Knowledge Base
    is ~25K tokens of cached prefix, and a triage call that reused none of it would pay full
    input price to read the same thing the conversation just read (ADR-0005).
    """
    chat = build_system_prompt(knowledge, today=today)
    return SystemPrompt(
        cached_sections=chat.cached_sections,
        volatile=f"{TRIAGE_INSTRUCTIONS}\n\n{build_volatile_block(today)}",
    )


def triage_brief(feedback: Feedback, conversation: Sequence[ModelMessage]) -> str:
    """What the Triage Agent is given to read: the Turn, and the Visitor's own words.

    The conversation comes out of the store already `refuse`-redacted (ADR-0006) — the Refuse
    Set never reached storage — and the comment went through the `full` profile when the
    Feedback was written, so there is nothing to strip here.
    """
    lines = [
        f"{message.role}: {message.content.strip()}"
        for message in conversation
        if message.role in CONVERSATION_ROLES and message.content.strip()
    ]
    transcript = "\n".join(lines) if lines else "(the Session holds no conversation)"
    comment = (
        f'The Visitor added: "{feedback.comment.strip()}"'
        if feedback.comment.strip()
        else "The Visitor added no comment."
    )
    return (
        "Conversation so far, oldest first:\n\n"
        f"{transcript}\n\n"
        f"The Visitor pressed thumbs-down on the Turn traced as {feedback.trace_id}. {comment}"
    )


def _json_object(answer: str) -> Mapping[str, Any] | None:
    """The JSON object in a model's answer, or `None`.

    A fenced block is unwrapped because a model told to answer with JSON sometimes answers
    with a code block containing JSON, and salvaging that is one line rather than a report in
    category `other`.
    """
    text = answer.strip()
    if text.startswith("```"):
        fenced = text.split("```")
        # ```json\n{...}\n``` splits into ("", "json\n{...}\n", ""); the language tag is the
        # first line of the block and is dropped with it.
        block = fenced[1] if len(fenced) > 1 else text
        if block.lstrip().casefold().startswith("json"):
            _, _, block = block.partition("\n")
        text = block
    try:
        parsed = json.loads(text.strip())
    except (json.JSONDecodeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _quotes(value: object) -> tuple[str, ...]:
    """The evidence, however the model chose to send it: a list, or a single quote."""
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if isinstance(value, list):
        return tuple(str(quote).strip() for quote in value if str(quote).strip())
    return ()


def parse_report(answer: str, *, feedback: Feedback, model: str) -> TriageReport:
    """The model's answer as a Triage Report — never an exception.

    A response that is not the schema is still a Cadre engineer's only record of a thumbs-down,
    so it becomes a report in category `other` carrying whatever the model did say. The same
    goes field by field: a category this build has no chip for is `other`, an unknown severity
    is medium, and an empty summary falls back to the raw text.
    """
    fields = _json_object(answer)
    if fields is None:
        logger.warning("The Triage Agent's model did not answer with the report schema")
        return TriageReport(
            id=feedback.id,
            session_id=feedback.session_id,
            trace_id=feedback.trace_id,
            category=FALLBACK_CATEGORY,
            summary=answer.strip(),
            severity=FALLBACK_SEVERITY,
            model=model,
        )
    category = str(fields.get("category") or "")
    severity = str(fields.get("severity") or "")
    summary = str(fields.get("summary") or "").strip()
    return TriageReport(
        id=feedback.id,
        session_id=feedback.session_id,
        trace_id=feedback.trace_id,
        category=(category if category in TRIAGE_CATEGORIES else FALLBACK_CATEGORY),
        summary=summary or answer.strip(),
        evidence=_quotes(fields.get("evidence")),
        suggested_kb_addition=str(fields.get("suggested_kb_addition") or "").strip(),
        suggested_eval_case=str(fields.get("suggested_eval_case") or "").strip(),
        severity=(severity if severity in TRIAGE_SEVERITIES else FALLBACK_SEVERITY),
        model=model,
    )


async def _ask(provider: ModelProvider, request: ProviderRequest) -> tuple[str, Usage]:
    """One model call, collected. The Triage Agent streams nothing to anybody — there is no
    Visitor waiting — so the deltas are joined and the usage kept for the log line."""
    answer: list[str] = []
    usage = Usage()
    async for event in provider.stream(request):
        if isinstance(event, TextDelta):
            answer.append(event.text)
        elif isinstance(event, Usage):
            usage = event
    return "".join(answer), usage


async def triage_feedback(
    event_data: Mapping[str, Any],
    *,
    store: ConversationStore,
    provider: ModelProvider,
    tracer: Tracer,
    knowledge: str,
    model: str,
    today: date | None = None,
) -> TriageReport | None:
    """Triage one Feedback document, or return `None` because there is nothing to triage.

    `event_data` is the document's fields as the Firestore trigger delivers them — the shape,
    not the SDK's wrapper, so the handler is the same code whatever delivers the event.
    `knowledge` is the rendered Knowledge Base block, compiled once when the process starts;
    `model` is the model id the provider is configured with, recorded on the report because a
    suggestion outlives the model that made it.
    """
    feedback = decode_feedback(event_data)
    if feedback is None or feedback.rating != "down":
        # The trigger fires on every write to the collection — a thumbs-up, a note added to
        # one, a Visitor changing their mind back. Returning here is what keeps the Triage
        # Agent's cost proportional to the thing it exists for.
        return None

    with session_context(feedback.session_id):
        # The stored document over the event's copy where both exist: it is the same document,
        # and reading it back means a report is written from what Firestore holds now rather
        # than from an event that has been sitting in a retry queue.
        stored = await store.get_feedback(feedback.session_id, feedback.trace_id)
        if stored is not None and stored.rating != "down":
            logger.info("The thumbs-down was changed before the Triage Agent read it")
            return None
        feedback = stored or feedback

        conversation = await store.load(feedback.session_id)
        request = ProviderRequest(
            prompt=build_triage_prompt(knowledge, today=today or datetime.now(tz=UTC).date()),
            messages=(ModelMessage(role="visitor", content=triage_brief(feedback, conversation)),),
            # No tools: the Triage Agent reads a conversation, it does not hold one.
            response_format=triage_response_format(),
            # The Session's own id, so this call routes to the upstream holding its cached
            # prefix (ADR-0002) — the one the Turn being triaged just warmed.
            session_id=feedback.session_id,
        )
        try:
            answer, usage = await _ask(provider, request)
        except ProviderError as failure:
            # Nobody is waiting on this, and the next thumbs-down is not far away: a provider
            # failure is a line in the log, not a raised exception that makes the platform
            # redeliver the event into the same outage.
            logger.error(
                "The Triage Agent could not reach the model",
                extra={"provider_detail": failure.detail},
            )
            return None

        report = await store.save_triage_report(
            parse_report(answer, feedback=feedback, model=model)
        )
        # The summary sits on the Trace it analyses, beside the Visitor's thumb and the cost
        # of the Turn, so Langfuse is one place rather than a third one (ADR-0005). The
        # boundary swallows whatever the vendor says about it.
        tracer.score(
            trace_id=report.trace_id,
            name=TRIAGE_SCORE_NAME,
            value=SEVERITY_SCORES[report.severity],
            comment=report.summary,
        )
        logger.info(
            "Triage Report written",
            extra={
                "triage_category": report.category,
                "triage_severity": report.severity,
                "input_tokens": usage.input_tokens,
                "cached_tokens": usage.cached_tokens,
                "cost_usd": usage.cost_usd,
                "model": model,
            },
        )
        return report
