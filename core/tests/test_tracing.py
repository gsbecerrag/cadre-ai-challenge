"""What a Turn is tagged with — seam S2, a pure function over what the Turn did.

Tags are the vocabulary a Cadre engineer filters a week of conversations by, so they are worth
pinning away from a running Turn: the same Turn always produces the same tags, in the same
order, whatever order the tools happened to run in.

The last test is the exception, and it is here rather than at S1 for a reason: a Visitor
closing the tab is the browser abandoning a stream, and the HTTP test client cannot express
that — it runs the whole Turn in-process before it hands the response back, so there is
nothing left to abandon. So that one drives `TurnRunner.run` directly and closes the async
generator, which is exactly what the ASGI server does when a connection drops.
"""

import asyncio
from collections.abc import AsyncGenerator
from datetime import date
from typing import cast

from core.adapters.memory_store import InMemoryConversationStore
from core.adapters.recording_tracer import RecordedScore, RecordingTracer
from core.adapters.stub_provider import StubModelProvider
from core.events import ChatEvent
from core.prompt import SystemPrompt, build_system_prompt
from core.provider import TextDelta, Usage
from core.tools import default_tools
from core.tracing import (
    FEEDBACK_SCORE_NAME,
    NOOP_TRACE,
    PROVIDER_ERROR_TAG,
    TOOL_TAGS,
    NoopTracer,
    TraceBoundary,
    TurnTrace,
    turn_tags,
)
from core.turn import TurnRunner

SPEND = Usage(input_tokens=12_400, output_tokens=48, cached_tokens=12_200, cost_usd=0.0031)
KNOWLEDGE_BLOCK = "[services#what-cadre-does] What Cadre does\nCadre AI is a consultancy."
SESSION = "sess-0100"


def test_a_turn_that_ran_no_tools_and_redacted_nothing_carries_no_tags() -> None:
    assert turn_tags([]) == ()


def test_each_tool_the_turn_ran_names_what_the_turn_did() -> None:
    """`escalate` is a refusal, `capture_lead` is a Lead, `show_walkthrough` is a card — the
    three things worth finding a week of conversations by."""
    assert turn_tags(["escalate"]) == ("escalated",)
    assert turn_tags(["capture_lead"]) == ("lead_captured",)
    assert turn_tags(["show_walkthrough"]) == ("walkthrough_shown",)


def test_the_tags_do_not_depend_on_the_order_the_tools_ran_in() -> None:
    """Two Turns that did the same things read the same in Langfuse; a tag list that followed
    the model's whim would make "escalated, lead_captured" and its reverse look like two
    different kinds of Turn."""
    assert turn_tags(["capture_lead", "escalate"]) == turn_tags(["escalate", "capture_lead"])


def test_a_tool_called_twice_in_one_turn_is_still_one_tag() -> None:
    assert turn_tags(["capture_lead", "capture_lead"]) == ("lead_captured",)


def test_a_tool_name_the_registry_does_not_know_earns_no_tag() -> None:
    """A model can ask for any tool name it likes. An invented one is not a new tag in
    Langfuse — it comes back to the model as a result it can correct (ADR-0004)."""
    assert turn_tags(["teleport_the_visitor"]) == ()


def test_the_language_an_escalation_answered_in_is_a_tag() -> None:
    """Known for free, because the Escalation copy is looked up per language — and "how many
    Spanish Turns end in a refusal" is then a filter rather than a research project."""
    assert turn_tags(["escalate"], "es") == ("escalated", "language:es")
    assert turn_tags(["escalate"], None) == ("escalated",)


def test_a_turn_that_failed_at_the_provider_says_so() -> None:
    assert PROVIDER_ERROR_TAG in turn_tags([], provider_error=True)


def test_the_redaction_manifest_becomes_one_tag_per_category_and_never_a_value() -> None:
    """Counts stay in metadata; the categories are tags, so "how often does a Visitor paste a
    card" is a filter over Traces (ADR-0006)."""
    tags = turn_tags([], redactions={"card": 2, "ssn": 1})

    assert tags == ("redacted:card", "redacted:ssn")
    assert not any("2" in tag for tag in tags)


def test_every_tool_the_assistant_can_call_has_a_tag_waiting_for_it() -> None:
    """Ticket 11's `offer_live_handover` is in the table already: a Hand-over offer becomes a
    tag the day the tool is registered, with no change here or in the Turn."""
    assert TOOL_TAGS["offer_live_handover"] == "handover_offered"


def test_a_visitor_who_closes_the_tab_mid_turn_still_leaves_a_trace() -> None:
    """A closed tab is the one ending that leaves nothing else behind: the Turn is not stored,
    because it did not complete, and there is no `done` event to carry a cost. The Trace is the
    only record that the Visitor was here — so it is closed and tagged rather than left half
    open, it holds what the Visitor actually read, and the Session is still untouched."""
    store = InMemoryConversationStore()
    provider = StubModelProvider()
    provider.script(
        "what does cadre", [TextDelta("Cadre AI is"), TextDelta(" a consultancy."), SPEND]
    )
    recorder = RecordingTracer()

    def prompt() -> SystemPrompt:
        return build_system_prompt(KNOWLEDGE_BLOCK, today=date(2026, 8, 30))

    runner = TurnRunner(
        provider=provider,
        store=store,
        tools=default_tools(store),
        build_prompt=prompt,
        tracer=TraceBoundary(recorder),
        model="stub",
    )

    async def walk_away_after_the_first_frame() -> None:
        # `run` is annotated as the iterator its callers consume; closing one is what an ASGI
        # server does to the generator underneath when a connection drops.
        stream = runner.run(SESSION, "What does Cadre AI do?")
        turn = cast(AsyncGenerator[ChatEvent, None], stream)
        await anext(turn)
        await turn.aclose()

    asyncio.run(walk_away_after_the_first_frame())

    (trace,) = recorder.traces
    assert trace.finished
    assert "client_disconnected" in trace.tags
    assert trace.output_text == "Cadre AI is"
    assert [span.closed_with for span in trace.spans] == ["GeneratorExit"]
    assert asyncio.run(store.load(SESSION)) == ()


# ------------------------------------------------------------------ Feedback as a score


class TracerThatCannotScore:
    """A `Tracer` whose score call fails, which is what a Langfuse outage looks like from
    inside `POST /api/feedback`. A Visitor's thumb is recorded whatever the vendor does."""

    def start_turn(self, session_id: str, request_id: str, input_text: str) -> TurnTrace:
        return NOOP_TRACE

    def score(self, trace_id: str, name: str, value: float, comment: str = "") -> None:
        raise RuntimeError("Langfuse rejected the score")

    def shutdown(self) -> None:
        return


def test_feedback_reaches_the_tracer_as_a_score_on_the_turns_own_trace() -> None:
    """A thumbs-down is worth nothing next to the conversation it judges, so it is a score on
    that Trace — which is what makes "show me the Turns Visitors disliked" a filter."""
    recorder = RecordingTracer()

    TraceBoundary(recorder).score(
        trace_id="a" * 32, name=FEEDBACK_SCORE_NAME, value=0.0, comment="Missed the question."
    )

    assert recorder.scores == [
        RecordedScore(trace_id="a" * 32, name="feedback", value=0.0, comment="Missed the question.")
    ]


def test_a_visitors_comment_goes_through_the_full_redaction_profile_before_langfuse() -> None:
    """The same rule the Trace's own bodies obey (ADR-0006): a Visitor who types their email
    into the comment box has typed it to Cadre, not to an observability vendor."""
    recorder = RecordingTracer()

    TraceBoundary(recorder).score(
        trace_id="b" * 32,
        name=FEEDBACK_SCORE_NAME,
        value=1.0,
        comment="Great — mail me at jane@example.com",
    )

    (score,) = recorder.scores
    assert score.comment == "Great — mail me at [EMAIL_1]"
    assert "jane@example.com" not in score.comment


def test_a_tracer_that_cannot_score_does_not_fail_the_feedback_request() -> None:
    """The boundary's second rule, at the one call site outside a Turn: the Feedback document
    is written and the Visitor is thanked whether or not Langfuse is up."""
    TraceBoundary(TracerThatCannotScore()).score(
        trace_id="c" * 32, name=FEEDBACK_SCORE_NAME, value=0.0
    )


def test_scoring_with_tracing_off_records_nothing_and_raises_nothing() -> None:
    """`NoopTracer` is CI, `make dev` and every reviewer's laptop: the Feedback endpoint runs
    the identical code path there, and nothing leaves."""
    NoopTracer().score(trace_id="d" * 32, name=FEEDBACK_SCORE_NAME, value=1.0, comment="")
