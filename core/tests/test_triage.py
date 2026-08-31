"""The Triage Agent — seam S3: the handler with a fake event, a fake store and the stub provider.

The Firebase Function around it is four lines of decoding and wiring (`functions/main.py`);
everything worth a test is here, which is the whole reason the handler lives in `core` and
takes its seams as arguments (ADR-0005). Nothing in this file reaches Firestore, OpenRouter or
Langfuse: the store is the in-memory adapter, the provider is the scriptable stub returning a
structured-output fixture, and the tracer records what it was given.

The pure helpers — the JSON schema the call carries and the decoding of a Feedback document —
are seam S2 units at the bottom.
"""

import asyncio
import json
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

import pytest

from core.adapters.memory_store import InMemoryConversationStore
from core.adapters.recording_tracer import RecordingTracer
from core.adapters.stub_provider import StubModelProvider, StubResponse
from core.prompt import build_system_prompt
from core.provider import ModelMessage, TextDelta, Usage
from core.store import TRIAGE_CATEGORIES, Feedback, Rating, TriageReport
from core.triage import (
    SEVERITY_SCORES,
    TRIAGE_SCORE_NAME,
    decode_feedback,
    triage_feedback,
    triage_response_format,
)

# Obviously fake ids, in the shape the service issues them (constraint 5).
SESSION_ID = "sess-0000-triage"
TRACE_ID = "9f2c1d4e5a6b7c8d9e0f1a2b3c4d5e6f"
MODEL = "anthropic/claude-sonnet-5"
TODAY = date(2026, 8, 31)

KNOWLEDGE_BLOCK = (
    "[not-published#certifications] Certifications\n"
    "Cadre does not publish its security certifications.\n\n"
    "[services#ai-engineering] AI Engineering\n"
    "Automation, integrations and custom agents."
)

VISITOR_ASKED = "Do you have SOC 2?"
ASSISTANT_ANSWERED = "I can't confirm that [not-published#certifications]."
VISITOR_COMPLAINED = (
    "It just said it couldn't confirm anything — I needed the security basics for my vendor form."
)

# What the model returns when it answers the schema. The wording is the design reference's own
# sample report (docs/design/DESIGN-BRIEF.md §3.3), so the fixture reads like the real thing.
REPORT = {
    "category": "kb_gap",
    "summary": (
        "A Visitor asked for SOC 2 documentation. The Assistant escalated correctly but had no "
        "published security commitment to cite, so the Escalation was empty."
    ),
    "evidence": [VISITOR_ASKED, VISITOR_COMPLAINED],
    "suggested_kb_addition": (
        "Add the three data-security commitments to security#commitments so an Escalation can "
        "cite them."
    ),
    "suggested_eval_case": 'trap: "Do you have SOC 2?" -> escalate + cite security#commitments',
    "severity": "medium",
}


def feedback_document(rating: str = "down", comment: str = VISITOR_COMPLAINED) -> dict[str, Any]:
    """A `feedback/{trace_id}` document as the Firestore trigger delivers its fields."""
    return {
        "session_id": SESSION_ID,
        "trace_id": TRACE_ID,
        "rating": rating,
        "comment": comment,
        "changes": 0,
    }


def rated_session(
    rating: Rating = "down", comment: str = VISITOR_COMPLAINED
) -> InMemoryConversationStore:
    """A Session that produced one Turn, and the thumb a Visitor left on it."""
    store = InMemoryConversationStore()
    asyncio.run(
        store.append(
            SESSION_ID,
            (
                ModelMessage(role="visitor", content=VISITOR_ASKED),
                ModelMessage(role="assistant", content=ASSISTANT_ANSWERED),
            ),
            trace_id=TRACE_ID,
        )
    )
    asyncio.run(
        store.save_feedback(
            Feedback(session_id=SESSION_ID, trace_id=TRACE_ID, rating=rating, comment=comment)
        )
    )
    return store


def answering(*text: str) -> StubModelProvider:
    """A provider that answers any triage brief with this text and one usage block."""
    response: StubResponse = [
        *(TextDelta(fragment) for fragment in text),
        Usage(input_tokens=24_000, output_tokens=180, cached_tokens=23_000, cost_usd=0.012),
    ]
    return StubModelProvider(fallback=[response])


def run(
    store: InMemoryConversationStore,
    provider: StubModelProvider,
    document: Mapping[str, Any] | None = None,
    tracer: RecordingTracer | None = None,
) -> TriageReport | None:
    return asyncio.run(
        triage_feedback(
            document if document is not None else feedback_document(),
            store=store,
            provider=provider,
            tracer=tracer if tracer is not None else RecordingTracer(),
            knowledge=KNOWLEDGE_BLOCK,
            model=MODEL,
            today=TODAY,
        )
    )


def reports(store: InMemoryConversationStore) -> Sequence[TriageReport]:
    return asyncio.run(store.list_triage_reports())


def test_a_thumbs_up_writes_no_triage_report_and_never_calls_the_model() -> None:
    store = rated_session(rating="up", comment="")
    provider = answering(json.dumps(REPORT))

    assert run(store, provider, feedback_document(rating="up", comment="")) is None
    assert provider.calls == 0
    assert reports(store) == ()


def test_a_thumbs_down_writes_a_triage_report_carrying_every_field_of_the_schema() -> None:
    store = rated_session()
    provider = answering(json.dumps(REPORT))

    report = run(store, provider)

    assert report is not None
    # Keyed by the Feedback id, which is the Trace id: the report points at the Turn it
    # analysed without a join (ADR-0005).
    assert report.id == TRACE_ID
    assert report.session_id == SESSION_ID
    assert report.trace_id == TRACE_ID
    assert report.category == "kb_gap"
    assert report.summary == REPORT["summary"]
    assert report.evidence == tuple(REPORT["evidence"])
    assert report.suggested_kb_addition == REPORT["suggested_kb_addition"]
    assert report.suggested_eval_case == REPORT["suggested_eval_case"]
    assert report.severity == "medium"
    assert report.model == MODEL
    assert reports(store) == (report,)


def test_a_redelivered_event_overwrites_the_one_report_rather_than_writing_a_second() -> None:
    store = rated_session()
    provider = answering(json.dumps(REPORT))

    first = run(store, provider)
    second = run(store, provider)

    # Firestore triggers are at-least-once, so this is the ordinary case and not an edge one:
    # the report id is the Feedback id, and the second delivery writes the same document.
    assert first is not None and second is not None
    assert first.id == second.id == TRACE_ID
    assert reports(store) == (second,)


def test_a_malformed_model_response_becomes_an_other_report_with_the_raw_text() -> None:
    store = rated_session()
    provider = answering("The conversation looks fine to me.")

    report = run(store, provider)

    assert report is not None
    assert report.category == "other"
    assert report.summary == "The conversation looks fine to me."
    assert reports(store) == (report,)


def test_a_report_answered_inside_a_fenced_code_block_is_still_a_report() -> None:
    store = rated_session()
    provider = answering("```json\n", json.dumps(REPORT), "\n```")

    report = run(store, provider)

    # A model told to answer with JSON sometimes answers with a code block containing JSON.
    # Salvaging that is one line here and the difference between a real report and an `other`.
    assert report is not None
    assert report.category == "kb_gap"
    assert report.summary == REPORT["summary"]


def test_the_model_call_asks_for_the_report_as_structured_output_against_the_schema() -> None:
    store = rated_session()
    provider = answering(json.dumps(REPORT))

    run(store, provider)

    assert provider.calls == 1
    request = provider.requests[0]
    assert request.response_format == triage_response_format()
    # One call, and no tools: the Triage Agent reads a conversation, it does not hold one.
    assert request.tools == ()


def test_the_triage_call_reuses_the_chat_prompts_cached_prefix_byte_for_byte() -> None:
    store = rated_session()
    provider = answering(json.dumps(REPORT))

    run(store, provider)

    # ADR-0005: the same cached prefix as a chat Turn, so the triage call lands on the cache
    # the conversation just paid to write.
    assert (
        provider.requests[0].prompt.cached
        == build_system_prompt(KNOWLEDGE_BLOCK, today=TODAY).cached
    )


def test_the_agent_reads_the_conversation_and_the_visitors_own_words() -> None:
    store = rated_session()
    provider = answering(json.dumps(REPORT))

    run(store, provider)

    brief = provider.requests[0].messages[-1].content
    assert VISITOR_ASKED in brief
    assert ASSISTANT_ANSWERED in brief
    assert VISITOR_COMPLAINED in brief


def test_the_summary_is_posted_back_to_the_trace_the_feedback_judges() -> None:
    store = rated_session()
    provider = answering(json.dumps(REPORT))
    tracer = RecordingTracer()

    report = run(store, provider, tracer=tracer)

    assert report is not None
    assert len(tracer.scores) == 1
    score = tracer.scores[0]
    assert score.trace_id == TRACE_ID
    assert score.name == TRIAGE_SCORE_NAME
    assert score.value == SEVERITY_SCORES["medium"]
    assert score.comment == report.summary


# ------------------------------------------------------------------ S2: the pure helpers


def test_the_triage_schema_offers_the_model_every_category_a_report_may_carry() -> None:
    schema = triage_response_format()["json_schema"]["schema"]

    assert tuple(schema["properties"]["category"]["enum"]) == TRIAGE_CATEGORIES
    assert tuple(schema["properties"]["severity"]["enum"]) == ("low", "medium", "high")
    # Strict structured output: every field is required, and an absent suggestion is written
    # as an empty string rather than a missing key (docs/research/openrouter-facts.md).
    assert set(schema["required"]) == set(schema["properties"])
    assert schema["additionalProperties"] is False


def test_a_feedback_document_decodes_into_the_feedback_it_records() -> None:
    assert decode_feedback(feedback_document()) == Feedback(
        session_id=SESSION_ID,
        trace_id=TRACE_ID,
        rating="down",
        comment=VISITOR_COMPLAINED,
    )


@pytest.mark.parametrize(
    "document",
    [
        {},
        {"session_id": SESSION_ID, "trace_id": TRACE_ID},
        {"session_id": SESSION_ID, "trace_id": TRACE_ID, "rating": "meh"},
        {"session_id": SESSION_ID, "rating": "down"},
        {"trace_id": TRACE_ID, "rating": "down"},
    ],
)
def test_a_document_that_is_not_feedback_decodes_to_nothing(document: Mapping[str, Any]) -> None:
    # A deleted document delivers an empty value, and a schema this build does not recognise
    # is not something to guess at: either way there is no Feedback to triage.
    assert decode_feedback(document) is None
