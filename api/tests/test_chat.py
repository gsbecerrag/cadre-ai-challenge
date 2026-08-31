"""One Turn through the chat endpoint — seam S1, with the stub provider and in-memory store."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.session import SESSION_COOKIE
from api.tests.conftest import LogReader, sse_events
from core.adapters.knowledge_files import FileKnowledgeSource
from core.adapters.stub_provider import StubModelProvider
from core.config import MissingConfigurationError, Settings
from core.provider import ProviderError, TextDelta, ToolCall, Usage
from core.turn import GRACEFUL_STOP, PROVIDER_ERROR_MESSAGE

ANSWER = "Cadre AI is a consultancy focused on revenue growth and EBITDA."
CITATION = " [services#what-cadre-does]"
SPEND = Usage(input_tokens=12_400, output_tokens=48, cached_tokens=12_200, cost_usd=0.0031)

ESCALATE = ToolCall(
    id="call-0100",
    name="escalate",
    arguments={
        "reason": "Cadre does not publish pricing for its engagements.",
        "next_step": "Write hello@gocadre.ai or call (619) 324-3223 [contact#how-to-reach-cadre].",
    },
)


def test_a_turn_streams_the_answer_as_text_deltas_and_ends_with_usage(
    client: TestClient, provider: StubModelProvider
) -> None:
    provider.script("what does cadre", [TextDelta(ANSWER), TextDelta(CITATION), SPEND])

    response = client.post("/api/chat", json={"message": "What does Cadre AI do?"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert sse_events(response) == [
        ("text", {"delta": ANSWER}),
        ("text", {"delta": CITATION}),
        (
            "done",
            {
                "trace_id": None,
                "usage": {
                    "input_tokens": 12_400,
                    "output_tokens": 48,
                    "cached_tokens": 12_200,
                    "cost_usd": 0.0031,
                },
            },
        ),
    ]


def test_a_tool_call_is_marked_in_the_stream_before_the_answer_that_follows_it(
    client: TestClient, provider: StubModelProvider
) -> None:
    provider.script("what does it cost", [ESCALATE], [TextDelta(ANSWER), SPEND])

    response = client.post("/api/chat", json={"message": "What does it cost?"})

    events = sse_events(response)
    assert [name for name, _ in events] == ["tool", "escalation", "tool", "text", "done"]
    assert events[0] == ("tool", {"name": "escalate", "status": "started"})
    assert events[2] == ("tool", {"name": "escalate", "status": "finished"})
    assert events[1][1]["body"] == ESCALATE.arguments["reason"]
    # The marker becomes a chip, so it must not also be left sitting in the prose.
    assert events[1][1]["next_step"] == "Write hello@gocadre.ai or call (619) 324-3223."
    assert events[1][1]["citations"] == ["contact#how-to-reach-cadre"]


def test_the_tool_result_is_fed_back_so_the_model_can_answer_with_it(
    client: TestClient, provider: StubModelProvider
) -> None:
    provider.script("what does it cost", [ESCALATE], [TextDelta(ANSWER), SPEND])

    client.post("/api/chat", json={"message": "What does it cost?"})

    second_call = provider.requests[1]
    assert [message.role for message in second_call.messages] == ["visitor", "assistant", "tool"]
    assert second_call.messages[-1].tool_call_id == ESCALATE.id


def test_a_provider_failure_is_one_user_safe_error_event_and_never_the_providers_words(
    client: TestClient, provider: StubModelProvider
) -> None:
    provider.script(
        "break it",
        [TextDelta("Let me check that"), ProviderError("HTTP 502 upstream: model_not_found")],
    )

    response = client.post("/api/chat", json={"message": "break it"})

    events = sse_events(response)
    assert [name for name, _ in events] == ["text", "error"]
    assert events[-1] == ("error", {"message": PROVIDER_ERROR_MESSAGE})
    assert "502" not in response.text
    assert "Traceback" not in response.text


def test_the_loop_never_asks_the_provider_more_than_four_times_in_one_turn(
    client: TestClient, provider: StubModelProvider
) -> None:
    """A model that keeps asking for tools must not be able to spend a Turn without end."""
    provider.script("loop forever", [ESCALATE])

    response = client.post("/api/chat", json={"message": "loop forever"})

    assert provider.calls == 4
    events = sse_events(response)
    assert events[-2] == ("text", {"delta": GRACEFUL_STOP})
    assert events[-1][0] == "done"


def test_the_first_turn_issues_a_session_cookie_the_browser_cannot_read(
    client: TestClient, provider: StubModelProvider
) -> None:
    provider.script("hello", [TextDelta(ANSWER), SPEND])

    response = client.post("/api/chat", json={"message": "hello"})

    assert response.cookies[SESSION_COOKIE]
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "Secure" in response.headers["set-cookie"]


def test_a_later_turn_in_the_same_session_carries_the_earlier_messages(
    client: TestClient, provider: StubModelProvider
) -> None:
    provider.script("hello", [TextDelta("Hi there."), SPEND])
    provider.script("and again", [TextDelta(ANSWER), SPEND])

    client.post("/api/chat", json={"message": "hello"})
    client.post("/api/chat", json={"message": "and again"})

    latest = provider.requests[-1]
    assert [message.content for message in latest.messages] == [
        "hello",
        "Hi there.",
        "and again",
    ]


def test_a_turn_from_another_session_is_never_surfaced(
    client: TestClient, provider: StubModelProvider
) -> None:
    provider.script("hello", [TextDelta("Hi there."), SPEND])
    client.post("/api/chat", json={"message": "hello"})
    client.cookies.clear()

    client.post("/api/chat", json={"message": "hello"})

    assert [message.content for message in provider.requests[-1].messages] == ["hello"]


def test_an_empty_message_is_not_a_turn(client: TestClient) -> None:
    response = client.post("/api/chat", json={"message": "   "})

    assert response.status_code == 422


def test_the_turn_is_logged_with_its_session_id(
    client: TestClient, provider: StubModelProvider, captured_logs: LogReader
) -> None:
    provider.script("hello", [TextDelta(ANSWER), SPEND])

    client.post("/api/chat", json={"message": "hello"})

    turn_lines = [record for record in captured_logs() if record["logger"] == "cadre.turn"]
    assert turn_lines and all(record["session_id"] for record in turn_lines)
    assert all(record["request_id"] for record in turn_lines)


def test_the_assistant_refuses_to_start_without_a_knowledge_base(
    tmp_path: Path, settings: Settings, web_dist: Path
) -> None:
    """An empty Knowledge Base is silent — the prompt still assembles, and the Assistant then
    answers from nothing at all. Better to refuse to start, naming where it looked."""
    empty = tmp_path / "no-knowledge-here"
    empty.mkdir()

    with pytest.raises(MissingConfigurationError) as refusal:
        create_app(settings=settings, web_dist=web_dist, knowledge=FileKnowledgeSource(empty))

    assert str(empty) in str(refusal.value)
