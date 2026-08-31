"""Every Turn is a Trace — seam S1, with the stub provider, the in-memory store and a
recording tracer standing in for Langfuse.

No test here reaches Langfuse. The `Tracer` seam is injected the same way the `ModelProvider`
and the `ConversationStore` are, so what a Cadre engineer would open in Langfuse is asserted
here as the calls the seam received: one Trace per Turn, named, on the Session, tagged with
what the Turn did, carrying the cost the provider reported, with a span per provider call and
per tool execution — and with the Visitor's own words masked by the `full` Redaction Profile
before they ever leave the process.

Every personal value here is obviously fake.
"""

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.tests.conftest import sse_events
from core.adapters.memory_store import InMemoryConversationStore
from core.adapters.recording_tracer import RecordingTracer
from core.adapters.stub_provider import StubModelProvider
from core.config import Settings
from core.provider import ProviderError, TextDelta, ToolCall, Usage
from core.tracing import TRACE_NAME, ProviderSpan, ToolSpan, Tracer, TurnTrace
from core.turn import PROVIDER_ERROR_MESSAGE

SPEND = Usage(input_tokens=12_400, output_tokens=48, cached_tokens=12_200, cost_usd=0.0031)
SECOND_SPEND = Usage(input_tokens=13_100, output_tokens=61, cached_tokens=12_200, cost_usd=0.0009)

ANSWER = "Cadre AI is a consultancy focused on revenue growth and EBITDA."
CITED_ANSWER = f"{ANSWER} [services#what-cadre-does]"

# Obviously fake, and the point of the masking test: what a Visitor pastes into the chat is
# what a Trace would otherwise carry to a third party (ADR-0006).
VISITOR_EMAIL = "jane@example.com"
EMAIL_TOKEN = "[EMAIL_1]"

ESCALATE = ToolCall(
    id="call-0600",
    name="escalate",
    arguments={
        "reason": "pricing",
        "known": "The 45-day Intensive is the engagement behind that question.",
        "next_step": "Write hello@gocadre.ai [contact#how-to-reach-cadre].",
        "language": "en",
    },
)

WALKTHROUGH = ToolCall(
    id="call-0601",
    name="show_walkthrough",
    arguments={
        "title": "See your agents' results in the Portal",
        "steps": [
            "Open the Cadre Portal [portal#how-to-access-the-portal]",
            "Go to Agents in the left menu",
        ],
        "destination": "portal.agents",
    },
)

CAPTURE_LEAD = ToolCall(
    id="call-0602",
    name="capture_lead",
    arguments={"name": "Jane Doe", "email": VISITOR_EMAIL, "industry_fit": "Manufacturing"},
)


class BrokenTracer:
    """A `Tracer` that fails at every call, which is what a Langfuse outage looks like from
    inside a Turn. A Visitor's answer does not depend on an observability vendor."""

    def start_turn(self, session_id: str, request_id: str, input_text: str) -> TurnTrace:
        raise RuntimeError("Langfuse is unreachable")

    def shutdown(self) -> None:
        raise RuntimeError("Langfuse is unreachable")


class HalfBrokenTracer:
    """Worse than an outage: a tracer that starts a Trace and then fails on everything else,
    so the failure arrives in the middle of a streamed answer."""

    def start_turn(self, session_id: str, request_id: str, input_text: str) -> TurnTrace:
        return _FailingTrace()

    def shutdown(self) -> None:
        raise RuntimeError("the export never happened")


class _FailingTrace:
    @property
    def trace_id(self) -> str | None:
        raise RuntimeError("no trace id")

    @contextmanager
    def provider_span(self, model: str, iteration: int) -> Iterator[ProviderSpan]:
        raise RuntimeError("span rejected")
        yield  # pragma: no cover — unreachable, and makes this a generator function

    @contextmanager
    def tool_span(self, name: str) -> Iterator[ToolSpan]:
        raise RuntimeError("span rejected")
        yield  # pragma: no cover — unreachable, and makes this a generator function

    def finish(
        self,
        output_text: str,
        usage: Usage,
        tags: Sequence[str],
        metadata: Mapping[str, Any],
    ) -> None:
        raise RuntimeError("Trace rejected")


@pytest.fixture
def tracer() -> RecordingTracer:
    return RecordingTracer()


@pytest.fixture
def traced_client(
    settings: Settings,
    web_dist: Path,
    provider: StubModelProvider,
    store: InMemoryConversationStore,
    tracer: RecordingTracer,
) -> Iterator[TestClient]:
    """The application with tracing on, recording instead of sending."""
    app = create_app(
        settings=settings, web_dist=web_dist, provider=provider, store=store, tracer=tracer
    )
    with TestClient(app, base_url="https://testserver") as test_client:
        yield test_client


def test_a_turn_is_one_trace_on_the_session_it_belongs_to(
    traced_client: TestClient, provider: StubModelProvider, tracer: RecordingTracer
) -> None:
    """A Session in Langfuse is a conversation, and a Trace inside it is one Turn — so the
    Session id has to be the one the cookie carries, not a per-Turn id."""
    provider.script("what does cadre", [TextDelta(ANSWER), SPEND])

    traced_client.post("/api/chat", json={"message": "What does Cadre AI do?"})
    traced_client.post("/api/chat", json={"message": "What does Cadre AI do next?"})

    assert len(tracer.traces) == 2
    first, second = tracer.traces
    assert [trace.name for trace in tracer.traces] == [TRACE_NAME, TRACE_NAME]
    assert first.session_id == second.session_id
    assert first.request_id and first.request_id != second.request_id
    assert first.finished and second.finished


def test_the_trace_carries_the_cost_and_the_tokens_the_provider_reported(
    traced_client: TestClient, provider: StubModelProvider, tracer: RecordingTracer
) -> None:
    """The cost is the one OpenRouter reported, summed over the Turn's provider calls, never
    an estimate from a price table (ADR-0002)."""
    provider.script("what does it cost", [ESCALATE, SPEND], [TextDelta(ANSWER), SECOND_SPEND])

    traced_client.post("/api/chat", json={"message": "What does it cost?"})

    (trace,) = tracer.traces
    assert trace.usage == SPEND + SECOND_SPEND
    assert trace.usage.cost_usd == pytest.approx(0.0040)


def test_the_trace_has_a_span_for_each_provider_call_and_each_tool_execution(
    traced_client: TestClient, provider: StubModelProvider, tracer: RecordingTracer
) -> None:
    """Two provider calls and one tool ran, so an engineer reading the Trace can see where the
    Turn's time and money went rather than one opaque block."""
    provider.script("what does it cost", [ESCALATE, SPEND], [TextDelta(ANSWER), SECOND_SPEND])

    traced_client.post("/api/chat", json={"message": "What does it cost?"})

    (trace,) = tracer.traces
    assert [(span.kind, span.name) for span in trace.spans] == [
        ("provider", "stub"),
        ("tool", "escalate"),
        ("provider", "stub"),
    ]
    assert [span.usage for span in trace.spans if span.kind == "provider"] == [SPEND, SECOND_SPEND]
    assert [span.produced_events for span in trace.spans if span.kind == "tool"] == [True]


@pytest.mark.parametrize(
    ("call", "tag"),
    [
        (ESCALATE, "escalated"),
        (WALKTHROUGH, "walkthrough_shown"),
        (CAPTURE_LEAD, "lead_captured"),
    ],
)
def test_the_trace_is_tagged_with_what_the_turn_did(
    traced_client: TestClient,
    provider: StubModelProvider,
    tracer: RecordingTracer,
    call: ToolCall,
    tag: str,
) -> None:
    """Tags are how a Cadre engineer finds the Turns worth reading: the ones that refused, the
    ones that captured a Lead, the ones that showed a Walkthrough Card."""
    provider.script("i need", [call, SPEND], [TextDelta(ANSWER), SECOND_SPEND])

    traced_client.post("/api/chat", json={"message": "I need help with that"})

    (trace,) = tracer.traces
    assert tag in trace.tags


def test_an_escalation_tags_the_language_it_answered_in(
    traced_client: TestClient, provider: StubModelProvider, tracer: RecordingTracer
) -> None:
    """The Escalation copy is looked up per language, so the language the Visitor was answered
    in is known for free — and "how many Spanish Turns end in a refusal" is then a filter."""
    spanish = ToolCall(
        id=ESCALATE.id, name=ESCALATE.name, arguments={**ESCALATE.arguments, "language": "es"}
    )
    provider.script("cuánto cuesta", [spanish, SPEND], [TextDelta(ANSWER), SECOND_SPEND])

    traced_client.post("/api/chat", json={"message": "¿Cuánto cuesta?"})

    (trace,) = tracer.traces
    assert "language:es" in trace.tags


def test_the_trace_records_the_kb_sections_the_turn_cited(
    traced_client: TestClient, provider: StubModelProvider, tracer: RecordingTracer
) -> None:
    """Which KB Sections an answer stood on is the question every groundedness argument starts
    from, and the markers are already in the answer — so the Trace keeps them as ids."""
    provider.script("what does cadre", [TextDelta(CITED_ANSWER), SPEND])

    traced_client.post("/api/chat", json={"message": "What does Cadre AI do?"})

    (trace,) = tracer.traces
    assert trace.metadata["citations"] == ["services#what-cadre-does"]


def test_the_trace_input_and_output_are_masked_by_the_full_redaction_profile(
    traced_client: TestClient, provider: StubModelProvider, tracer: RecordingTracer
) -> None:
    """Langfuse Cloud is somebody other than the Strategist handling the Lead, so a Trace gets
    the `full` profile: the address becomes a token, and the token is stable within the text
    so the conversation still reads (ADR-0006). The Lead keeps the address, the Trace does
    not."""
    echoed = f"Thanks — I have {VISITOR_EMAIL} on file."
    provider.script("my email", [TextDelta(echoed), SPEND])

    traced_client.post("/api/chat", json={"message": f"my email is {VISITOR_EMAIL}"})

    (trace,) = tracer.traces
    assert VISITOR_EMAIL not in trace.input_text
    assert VISITOR_EMAIL not in trace.output_text
    assert trace.input_text == f"my email is {EMAIL_TOKEN}"
    assert trace.output_text == f"Thanks — I have {EMAIL_TOKEN} on file."


def test_the_trace_carries_the_redaction_manifest_of_the_turn(
    traced_client: TestClient, provider: StubModelProvider, tracer: RecordingTracer
) -> None:
    """Counts per category and never a value, so "how often do Visitors paste things they
    should not" is a number nobody has to read a conversation to get (ADR-0006)."""
    provider.script("my card", [TextDelta(ANSWER), SPEND])

    traced_client.post(
        "/api/chat", json={"message": "my card is 4111 1111 1111 1111, can you store it?"}
    )

    (trace,) = tracer.traces
    assert trace.metadata["redactions"] == {"card": 1}
    assert "redacted:card" in trace.tags


def test_the_done_event_carries_the_trace_id_so_feedback_can_attach_to_it(
    traced_client: TestClient, provider: StubModelProvider, tracer: RecordingTracer
) -> None:
    """Feedback (ticket 12) is a thumbs-up or down on the Trace of the Turn it judges, so the
    browser has to be told which Trace it just watched."""
    provider.script("what does cadre", [TextDelta(ANSWER), SPEND])

    response = traced_client.post("/api/chat", json={"message": "What does Cadre AI do?"})

    (done,) = [data for name, data in sse_events(response) if name == "done"]
    (trace,) = tracer.traces
    assert done["trace_id"] == trace.trace_id
    assert isinstance(done["trace_id"], str)


def test_a_provider_error_is_still_a_trace_and_is_tagged_as_one(
    traced_client: TestClient, provider: StubModelProvider, tracer: RecordingTracer
) -> None:
    """The Turns worth reading first are the ones that failed. A failed Turn is stored
    nowhere, so if it is not on the Trace it is nowhere at all."""
    provider.script("what does cadre", [TextDelta("Cadre AI is"), ProviderError("upstream 502")])

    response = traced_client.post("/api/chat", json={"message": "What does Cadre AI do?"})

    assert [name for name, _ in sse_events(response)] == ["text", "error"]
    (trace,) = tracer.traces
    assert trace.finished
    assert "provider_error" in trace.tags
    # What the Visitor read, in the order they read it: the half-written answer, then the
    # apology that replaced the rest of it. The `full` profile is applied blind, so Cadre's own
    # contact details in the fixed copy are tokenised along with everything else — losing a
    # published phone number from a Trace is the harmless half of a boundary that cannot be
    # talked into an exception.
    assert trace.output_text.startswith("Cadre AI is")
    assert PROVIDER_ERROR_MESSAGE.split(" Please try again")[0] in trace.output_text


def test_the_instance_flushes_its_traces_on_the_way_out(
    settings: Settings,
    web_dist: Path,
    provider: StubModelProvider,
    store: InMemoryConversationStore,
    tracer: RecordingTracer,
) -> None:
    """Cloud Run reclaims an instance minutes after the last Turn, and the SDK exports from a
    background thread that gets no CPU once the request is over. A Turn whose Trace never left
    the container is a Turn nobody can read, so the instance flushes on its way out."""
    provider.script("what does cadre", [TextDelta(ANSWER), SPEND])
    app = create_app(
        settings=settings, web_dist=web_dist, provider=provider, store=store, tracer=tracer
    )

    with TestClient(app, base_url="https://testserver") as client:
        client.post("/api/chat", json={"message": "What does Cadre AI do?"})
        assert tracer.shutdowns == 0

    assert tracer.shutdowns == 1


def test_a_failed_turn_keeps_what_it_had_already_spent_and_streamed(
    traced_client: TestClient, provider: StubModelProvider, tracer: RecordingTracer
) -> None:
    """A Turn that failed halfway still cost money and still put words on the screen. Both
    belong on the Trace: the spend because it was spent, the words because they are what the
    Visitor read before the apology. The span is marked with what went wrong, so the failure
    is visible in Langfuse where the time went, not only on the Trace."""
    provider.script(
        "what does cadre",
        [TextDelta("Cadre AI is a consultancy"), SPEND, ProviderError("upstream 502")],
    )

    traced_client.post("/api/chat", json={"message": "What does Cadre AI do?"})

    (trace,) = tracer.traces
    assert trace.usage == SPEND
    assert "Cadre AI is a consultancy" in trace.output_text
    assert [span.closed_with for span in trace.spans] == ["ProviderError"]


def test_a_turn_is_served_normally_when_langfuse_is_not_configured(
    client: TestClient, provider: StubModelProvider
) -> None:
    """No keys is the default everywhere but the deployed service — CI, `make dev`, a
    reviewer's laptop — so tracing off has to be a no-op and not a startup failure."""
    provider.script("what does cadre", [TextDelta(ANSWER), SPEND])

    response = client.post("/api/chat", json={"message": "What does Cadre AI do?"})

    events = sse_events(response)
    assert [name for name, _ in events] == ["text", "done"]
    assert events[-1][1]["trace_id"] is None


@pytest.mark.parametrize(
    "broken", [BrokenTracer(), HalfBrokenTracer()], ids=["refuses-the-trace", "fails-midway"]
)
def test_a_tracer_that_fails_cannot_break_a_turn(
    settings: Settings,
    web_dist: Path,
    provider: StubModelProvider,
    store: InMemoryConversationStore,
    broken: Tracer,
) -> None:
    """Observability is not on the Visitor's critical path. Whatever the tracer does — refuse
    the Trace, fail halfway through the stream — the answer arrives and the Turn is stored."""
    provider.script("what does cadre", [TextDelta(ANSWER), SPEND])
    app = create_app(
        settings=settings, web_dist=web_dist, provider=provider, store=store, tracer=broken
    )

    with TestClient(app, base_url="https://testserver") as client:
        response = client.post("/api/chat", json={"message": "What does Cadre AI do?"})

    events = sse_events(response)
    assert [name for name, _ in events] == ["text", "done"]
    assert events[0][1]["delta"] == ANSWER
    assert events[-1][1]["trace_id"] is None
