"""Lead capture and the Qualification Score — seam S1, stub provider and in-memory store.

The Assistant is told to call `capture_lead` the moment a Visitor shares a Contact Detail, and
these tests are what the Turn does with that call: one Lead per Session, the Contact Details
kept raw because the product exists to collect them, the signals kept as the Assistant learned
them, and the score counted in code from the signals (ADR-0009).

Every personal value here is obviously fake.
"""

import asyncio
import re
from datetime import date

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.chat import create_chat_router
from api.session import SESSION_COOKIE, session_id_from_cookie
from api.tests.conftest import COOKIE_SECRET, sse_events
from core.adapters.memory_store import InMemoryConversationStore
from core.adapters.stub_provider import StubModelProvider
from core.prompt import build_system_prompt
from core.provider import TextDelta, ToolCall, Usage
from core.tools import default_tools
from core.turn import TurnRunner

SPEND = Usage(input_tokens=12_400, output_tokens=48, cached_tokens=12_200, cost_usd=0.0031)
ACKNOWLEDGEMENT = "Thanks — I have that. Supplier paperwork is exactly where agents earn back time."

KNOWLEDGE_BLOCK = "[services#what-cadre-does] What Cadre does\nCadre AI is a consultancy."

# What the Assistant volunteers after one exchange: five Contact Details and three of the five
# Qualification Signals. Fake values only — a real address never belongs in a fixture.
FULL_CAPTURE = ToolCall(
    id="call-0900",
    name="capture_lead",
    arguments={
        "name": "Jane Doe",
        "email": "jane@example.com",
        "company": "Acme Manufacturing",
        "phone": "+1 555 0100",
        "role": "VP of Operations",
        "industry_fit": "Manufacturing & Logistics",
        "company_size_or_role": "VP of Operations at roughly 300 people",
        "initiative_or_pain": "supplier paperwork eats three days a week",
    },
)

FIRST_CAPTURE = ToolCall(
    id="call-0901",
    name="capture_lead",
    arguments={
        "name": "Jane Doe",
        "email": "jane@example.com",
        "industry_fit": "Manufacturing & Logistics",
    },
)

LATER_CAPTURE = ToolCall(
    id="call-0902",
    name="capture_lead",
    arguments={
        "phone": "+1 555 0100",
        "initiative_or_pain": "supplier paperwork eats three days a week",
        "timeline_or_budget": "wants something running this quarter",
    },
)

SIGNALS_ONLY_CAPTURE = ToolCall(
    id="call-0903",
    name="capture_lead",
    arguments={
        "industry_fit": "Manufacturing & Logistics",
        "initiative_or_pain": "supplier paperwork eats three days a week",
    },
)


def stored_session_id(client: TestClient) -> str:
    """The id the store is keyed by, read back out of the signed cookie."""
    session_id = session_id_from_cookie(client.cookies[SESSION_COOKIE], COOKIE_SECRET)
    assert session_id is not None
    return session_id


def test_a_capture_lead_call_creates_a_lead_for_the_session_with_the_score_counted_in_code(
    client: TestClient, provider: StubModelProvider, store: InMemoryConversationStore
) -> None:
    provider.script("here are my details", [FULL_CAPTURE], [TextDelta(ACKNOWLEDGEMENT), SPEND])

    response = client.post("/api/chat", json={"message": "Here are my details."})

    assert [name for name, _ in sse_events(response)] == ["tool", "tool", "text", "done"]
    lead = asyncio.run(store.get_lead(stored_session_id(client)))
    assert lead is not None
    assert lead.session_id == stored_session_id(client)
    # Raw, because a tokenised email is a Lead a Strategist cannot call back.
    assert (lead.name, lead.email, lead.company, lead.phone, lead.role) == (
        "Jane Doe",
        "jane@example.com",
        "Acme Manufacturing",
        "+1 555 0100",
        "VP of Operations",
    )
    assert lead.signals == {
        "industry_fit": "Manufacturing & Logistics",
        "company_size_or_role": "VP of Operations at roughly 300 people",
        "initiative_or_pain": "supplier paperwork eats three days a week",
    }
    assert lead.score == 3
    assert lead.qualified is True


def test_the_assistant_is_told_the_lead_was_recorded_and_what_it_scored(
    client: TestClient, provider: StubModelProvider
) -> None:
    """The model reads the tool result on the next iteration; it is where the acknowledgement
    comes from. The score is reported to it, never assigned by it."""
    provider.script("here are my details", [FULL_CAPTURE], [TextDelta(ACKNOWLEDGEMENT), SPEND])

    client.post("/api/chat", json={"message": "Here are my details."})

    fed_back = provider.requests[1].messages[-1]
    assert fed_back.role == "tool"
    assert fed_back.tool_call_id == FULL_CAPTURE.id
    assert "3 of 5" in fed_back.content


def test_a_second_capture_lead_call_updates_the_same_lead_rather_than_creating_another(
    client: TestClient, provider: StubModelProvider, store: InMemoryConversationStore
) -> None:
    """A Lead is keyed by its Session. Details arrive over several Turns, and a later call that
    carries only a phone number must not erase the email the Visitor gave five minutes ago."""
    provider.script("my name is jane", [FIRST_CAPTURE], [TextDelta("Good to meet you."), SPEND])
    provider.script("my number is", [LATER_CAPTURE], [TextDelta(ACKNOWLEDGEMENT), SPEND])

    client.post("/api/chat", json={"message": "My name is Jane and I work in manufacturing."})
    after_first = asyncio.run(store.get_lead(stored_session_id(client)))
    assert after_first is not None
    assert after_first.score == 1
    assert after_first.qualified is False

    client.post("/api/chat", json={"message": "My number is on the way."})

    lead = asyncio.run(store.get_lead(stored_session_id(client)))
    assert lead is not None
    assert lead.email == "jane@example.com"
    assert lead.name == "Jane Doe"
    assert lead.phone == "+1 555 0100"
    assert set(lead.signals) == {"industry_fit", "initiative_or_pain", "timeline_or_budget"}
    assert lead.score == 3
    assert lead.qualified is True


def test_a_capture_lead_call_with_no_contact_detail_records_nothing_and_the_turn_carries_on(
    client: TestClient, provider: StubModelProvider, store: InMemoryConversationStore
) -> None:
    """A Lead with no way to reach the Visitor is not a Lead. The model gets a result it can
    correct — the same shape as a rejected Escalation — and the Visitor's Turn still finishes."""
    provider.script("we have a problem", [SIGNALS_ONLY_CAPTURE], [TextDelta("Understood."), SPEND])

    response = client.post("/api/chat", json={"message": "We have a problem with paperwork."})

    assert [name for name, _ in sse_events(response)] == ["tool", "tool", "text", "done"]
    assert asyncio.run(store.get_lead(stored_session_id(client))) is None
    fed_back = provider.requests[1].messages[-1]
    assert "no Lead was recorded" in fed_back.content


def mask_contact_details(message: str) -> str:
    """A stand-in for ticket 05's `refuse` Redaction Profile, turned up far past it: every
    email address and every digit in the Visitor's message is masked before the model and
    before the store. What survives it on the Lead is the point of the test below."""
    without_emails = re.sub(r"[^\s]+@[^\s]+", "[EMAIL]", message)
    return re.sub(r"\d", "#", without_emails)


def masked_client(provider: StubModelProvider, store: InMemoryConversationStore) -> TestClient:
    """The chat API with a `prepare_message` hook in front of it — the one place a Visitor
    message is rewritten before the provider call and before the store write."""
    runner = TurnRunner(
        provider=provider,
        store=store,
        tools=default_tools(store),
        build_prompt=lambda: build_system_prompt(KNOWLEDGE_BLOCK, today=date(2026, 8, 31)),
        prepare_message=mask_contact_details,
    )
    app = FastAPI()
    app.include_router(
        create_chat_router(runner, cookie_secret=COOKIE_SECRET, secure_cookie=False),
        prefix="/api",
    )
    return TestClient(app)


def test_the_lead_keeps_the_raw_contact_details_while_the_session_history_keeps_the_masked_text(
    provider: StubModelProvider, store: InMemoryConversationStore
) -> None:
    """Two paths, deliberately different (ADR-0006): what is stored as conversation goes
    through the Redaction Profile, and the typed Contact Details on the Lead do not — a
    Strategist has to be able to call the Visitor back."""
    provider.script("reach me at", [FULL_CAPTURE], [TextDelta(ACKNOWLEDGEMENT), SPEND])
    client = masked_client(provider, store)

    client.post(
        "/api/chat",
        json={"message": "Reach me at jane@example.com or +1 555 0100."},
    )

    session_id = stored_session_id(client)
    history = asyncio.run(store.load(session_id))
    visitor = next(message for message in history if message.role == "visitor")
    assert visitor.content == "Reach me at [EMAIL] or +# ### ####."
    assert "jane@example.com" not in visitor.content
    # The provider never saw the raw message either.
    assert "jane@example.com" not in provider.requests[0].messages[-1].content

    lead = asyncio.run(store.get_lead(session_id))
    assert lead is not None
    assert lead.email == "jane@example.com"
    assert lead.phone == "+1 555 0100"
