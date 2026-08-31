"""A Visitor's thumb becomes a Feedback document and a score — seam S1.

`POST /api/feedback` is the one endpoint a Visitor reaches that is not a Turn, and it is the
event source the Triage Agent runs on (ticket 14), so what is pinned here is the whole contract:
which Trace a Session may rate, what the document holds, what Langfuse is told, and what happens
when the Visitor changes their mind — once, and then not again.

Nothing here reaches Langfuse or Firestore: the `Tracer` seam records, the `ConversationStore`
is in memory, and the stub provider answers. Every personal value is obviously fake.
"""

import asyncio
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx2
import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.session import SESSION_COOKIE, session_id_from_cookie
from api.tests.conftest import COOKIE_SECRET, sse_events
from core.adapters.memory_store import InMemoryConversationStore
from core.adapters.recording_tracer import RecordingTracer
from core.adapters.stub_provider import StubModelProvider
from core.config import Settings
from core.provider import TextDelta, Usage
from core.store import Feedback
from core.tracing import FEEDBACK_SCORE_NAME

SPEND = Usage(input_tokens=12_400, output_tokens=48, cached_tokens=12_200, cost_usd=0.0031)
ANSWER = "Cadre AI is a consultancy focused on revenue growth and EBITDA."
QUESTION = "What does Cadre AI do?"

# Obviously fake, and the point of the redaction test: a Visitor types into the comment box
# the same things they type into the chat.
VISITOR_EMAIL = "jane@example.com"
EMAIL_TOKEN = "[EMAIL_1]"


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
    """The application with tracing on and recording, so a Turn has a Trace to be rated."""
    provider.script("what does cadre", [TextDelta(ANSWER), SPEND])
    app = create_app(
        settings=settings, web_dist=web_dist, provider=provider, store=store, tracer=tracer
    )
    with TestClient(app, base_url="https://testserver") as test_client:
        yield test_client


def answer_one_turn(client: TestClient, question: str = QUESTION) -> str:
    """Run a Turn and return the Trace id the `done` event carried — what a thumb rates."""
    response = client.post("/api/chat", json={"message": question})
    done = [payload for name, payload in sse_events(response) if name == "done"]
    trace_id = done[0]["trace_id"]
    assert isinstance(trace_id, str) and trace_id
    return trace_id


def session_of(client: TestClient) -> str:
    """The id the store is keyed by, read back out of the signed cookie."""
    session_id = session_id_from_cookie(client.cookies[SESSION_COOKIE], COOKIE_SECRET)
    assert session_id is not None
    return session_id


def feedback_on(store: InMemoryConversationStore, session_id: str, trace_id: str) -> Feedback:
    stored = asyncio.run(store.get_feedback(session_id, trace_id))
    assert stored is not None
    return stored


def rate(client: TestClient, trace_id: str, rating: str, comment: str = "") -> httpx2.Response:
    body: dict[str, Any] = {"trace_id": trace_id, "rating": rating}
    if comment:
        body["comment"] = comment
    return client.post("/api/feedback", json=body)


def test_a_thumbs_down_is_written_as_feedback_and_scored_on_the_turns_own_trace(
    traced_client: TestClient, store: InMemoryConversationStore, tracer: RecordingTracer
) -> None:
    """The two halves of the loop in one request: the document the Triage Agent runs on, and
    the score that makes "the Turns Visitors disliked" a filter in Langfuse."""
    trace_id = answer_one_turn(traced_client)

    response = rate(traced_client, trace_id, "down", comment="That missed my question.")

    assert response.status_code == 200
    body = response.json()
    assert body["rating"] == "down"
    assert body["changed"] is False
    assert body["feedback_id"]

    stored = feedback_on(store, session_of(traced_client), trace_id)
    assert stored.rating == "down"
    assert stored.trace_id == trace_id
    assert stored.session_id == session_of(traced_client)
    assert stored.comment == "That missed my question."

    (score,) = tracer.scores
    assert score.trace_id == trace_id
    assert score.name == FEEDBACK_SCORE_NAME
    assert score.value == 0.0
    assert score.comment == "That missed my question."


def test_a_thumbs_up_is_the_same_score_with_the_other_value(
    traced_client: TestClient, tracer: RecordingTracer
) -> None:
    """One score name, two values: the average is then the share of Turns Visitors liked."""
    trace_id = answer_one_turn(traced_client)

    response = rate(traced_client, trace_id, "up")

    assert response.status_code == 200
    (score,) = tracer.scores
    assert (score.name, score.value) == (FEEDBACK_SCORE_NAME, 1.0)


def test_a_comment_is_redacted_before_it_is_stored_or_traced(
    traced_client: TestClient, store: InMemoryConversationStore, tracer: RecordingTracer
) -> None:
    """The comment box is a text field a Visitor will put their email in. The `full` profile
    runs before the write and before the score, so neither Firestore nor Langfuse holds
    Contact Details typed where they were not asked for (ADR-0006)."""
    trace_id = answer_one_turn(traced_client)

    rate(traced_client, trace_id, "down", comment=f"Call me at {VISITOR_EMAIL} instead.")

    stored = feedback_on(store, session_of(traced_client), trace_id)
    assert stored.comment == f"Call me at {EMAIL_TOKEN} instead."
    assert VISITOR_EMAIL not in stored.comment
    (score,) = tracer.scores
    assert VISITOR_EMAIL not in score.comment


def test_a_trace_from_another_session_is_not_found_and_nothing_is_written(
    traced_client: TestClient, store: InMemoryConversationStore, tracer: RecordingTracer
) -> None:
    """A Trace id is not a capability: it travels to one browser in one `done` event, and
    rating somebody else's conversation would be writing on it. The answer is 404 rather than
    403, because a Session is not told whether a Trace it does not own exists at all."""
    someone_elses = answer_one_turn(traced_client)
    rated_by = session_of(traced_client)
    traced_client.cookies.clear()
    answer_one_turn(traced_client)

    response = rate(traced_client, someone_elses, "down")

    assert response.status_code == 404
    assert asyncio.run(store.get_feedback(rated_by, someone_elses)) is None
    assert not tracer.scores


def test_a_visitor_with_no_session_at_all_is_not_found_either(
    traced_client: TestClient, tracer: RecordingTracer
) -> None:
    """No cookie is not a fresh Session here: there is no Turn to rate, and minting one would
    say "that Trace is not yours" to a caller who has no conversation."""
    trace_id = answer_one_turn(traced_client)
    traced_client.cookies.clear()

    assert rate(traced_client, trace_id, "up").status_code == 404
    assert not tracer.scores


def test_a_visitor_may_change_their_mind_once_and_the_second_change_is_refused(
    traced_client: TestClient, store: InMemoryConversationStore, tracer: RecordingTracer
) -> None:
    """One Feedback per Trace: a second thumb corrects a misclick, and a third is a control
    being held down. The refusal is a conflict, and the Feedback that stands is the changed
    one — so the Triage Agent sees one rating per Turn, not a stream of them."""
    trace_id = answer_one_turn(traced_client)

    first = rate(traced_client, trace_id, "up")
    second = rate(traced_client, trace_id, "down", comment="On reflection, it missed.")
    third = rate(traced_client, trace_id, "up")

    assert first.json()["changed"] is False
    assert second.status_code == 200
    assert second.json()["changed"] is True
    assert second.json()["feedback_id"] == first.json()["feedback_id"]
    assert third.status_code == 409

    stored = feedback_on(store, session_of(traced_client), trace_id)
    assert stored.rating == "down"
    assert stored.comment == "On reflection, it missed."
    assert [score.value for score in tracer.scores] == [1.0, 0.0]


@pytest.mark.parametrize(
    "body",
    [
        {"trace_id": "a" * 32, "rating": "meh"},
        {"trace_id": "a" * 32},
        {"rating": "up"},
        {"trace_id": "a" * 32, "rating": "up", "comment": "x" * 501},
    ],
)
def test_a_body_the_contract_does_not_name_is_rejected_before_anything_is_written(
    traced_client: TestClient, tracer: RecordingTracer, body: dict[str, Any]
) -> None:
    """The rating is two words and the comment is one line; anything else is a client that
    has misunderstood, and it is refused before the Session is even looked up."""
    answer_one_turn(traced_client)

    assert traced_client.post("/api/feedback", json=body).status_code == 422
    assert not tracer.scores
