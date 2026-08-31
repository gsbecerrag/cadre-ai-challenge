"""The Console's Handover Requests — seam S1, with the `TokenVerifier` scripted.

These are the reads behind the Handover queue and the Callbacks tab. Two things are being
pinned here beyond "the endpoint answers":

*One collection, two views.* A Callback is not a second entity; it is a Handover Request whose
mode is `callback` (docs/design/README.md ruling), so the Callbacks tab is a query parameter
rather than a second table with its own drift.

*The conversation is read server-side.* A browser cannot read `sessions` — `firestore.rules`
denies it, deliberately, because a Session is the Visitor's side of the product — so the
request detail is where a Strategist gets the transcript, and it carries what the Visitor and
the Assistant said rather than the tool traffic between them.

The refusals (no token, bad token, not on the allowlist) are covered for every Console endpoint
including these by the parametrised tests in `test_console.py`, which read the routes off the
router itself. Every personal value here is obviously fake.
"""

import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.tests.test_console import ALLOWED_EMAILS, ANGEL, ANGEL_TOKEN, as_strategist
from core.adapters.fake_verifier import ScriptedTokenVerifier
from core.adapters.memory_store import InMemoryConversationStore
from core.adapters.stub_provider import StubModelProvider
from core.auth import StrategistIdentity
from core.config import Settings
from core.handover import HandoverRequest, LeadSnapshot
from core.provider import ModelMessage, ToolCall
from core.store import Lead

JANE = LeadSnapshot(
    name="Jane Doe",
    email="jane@example.com",
    company="Acme Manufacturing",
    phone="+1 555 0100",
    role="VP of Operations",
    signals={
        "industry_fit": "Manufacturing & Logistics",
        "initiative_or_pain": "supplier paperwork eats three days a week",
        "explicit_intent": "asked to speak to a strategist",
    },
    score=3,
    qualified=True,
)

SAM = LeadSnapshot(
    name="Sam Roe",
    email="sam@example.com",
    company="Northwind Realty",
    role="Managing Partner",
    signals={"industry_fit": "Real Estate", "timeline_or_budget": "this quarter"},
    score=2,
    qualified=False,
)

CALLBACK = HandoverRequest(
    id="hr-callback",
    session_id="session-0001",
    state="pending_strategist",
    mode="callback",
    prompt="Do you want to jump into a call with our experts?",
    lead=JANE,
)

# Obviously not a real Daily domain, the way a fixture's email is example.com.
ROOM_URL = "https://cadre-demo.daily.invalid/cadre-hr-video"

LIVE = HandoverRequest(
    id="hr-video",
    session_id="session-0002",
    state="pending_strategist",
    mode="video",
    room_url=ROOM_URL,
    lead=SAM,
)

# A Strategist whose Google profile carries no display name — allowlisted, verified, nameless.
NAMELESS = StrategistIdentity(uid="uid-dana", email="dana@example.com", name="")
NAMELESS_TOKEN = "id-token-dana"

# An offer the Visitor has not answered: no mode, and therefore nothing to join.
UNANSWERED = HandoverRequest(
    id="hr-unanswered",
    session_id="session-0004",
    state="offered",
    lead=SAM,
)

DECLINED = HandoverRequest(
    id="hr-declined",
    session_id="session-0003",
    state="declined",
    lead=SAM,
)

CONVERSATION = [
    ModelMessage(role="visitor", content="Supplier paperwork eats three days a week."),
    ModelMessage(
        role="assistant",
        content="",
        tool_calls=(ToolCall(id="call-1", name="capture_lead", arguments={"name": "Jane Doe"}),),
    ),
    ModelMessage(role="tool", content="The Lead was recorded.", tool_call_id="call-1"),
    ModelMessage(role="assistant", content="That is exactly where agents earn back time."),
]


@pytest.fixture
def verifier() -> ScriptedTokenVerifier:
    return ScriptedTokenVerifier({ANGEL_TOKEN: ANGEL, NAMELESS_TOKEN: NAMELESS})


@pytest.fixture
def console_client(
    settings: Settings,
    web_dist: Path,
    provider: StubModelProvider,
    store: InMemoryConversationStore,
    verifier: ScriptedTokenVerifier,
) -> Iterator[TestClient]:
    allowlisted = settings.model_copy(update={"admin_allowed_emails": ALLOWED_EMAILS})
    app = create_app(
        settings=allowlisted,
        web_dist=web_dist,
        provider=provider,
        store=store,
        verifier=verifier,
    )
    with TestClient(app, base_url="https://testserver") as client:
        yield client


def seed(store: InMemoryConversationStore, *requests: HandoverRequest) -> None:
    for request in requests:
        asyncio.run(store.create_handover(request))


def test_the_handover_queue_lists_every_request_newest_first(
    console_client: TestClient, store: InMemoryConversationStore
) -> None:
    """A work list: the Visitor who just asked is the one a Strategist should see at the top."""
    seed(store, CALLBACK, LIVE, DECLINED)

    response = console_client.get("/api/console/handovers", headers=as_strategist(ANGEL_TOKEN))

    assert response.status_code == 200
    assert [request["request_id"] for request in response.json()["handovers"]] == [
        "hr-declined",
        "hr-video",
        "hr-callback",
    ]


def test_the_callbacks_tab_is_the_callback_filter_of_the_same_collection(
    console_client: TestClient, store: InMemoryConversationStore
) -> None:
    """One Handover Request type with a mode, not two entities (the design ruling)."""
    seed(store, CALLBACK, LIVE, DECLINED)

    response = console_client.get(
        "/api/console/handovers", params={"mode": "callback"}, headers=as_strategist(ANGEL_TOKEN)
    )

    requests = response.json()["handovers"]
    assert [request["request_id"] for request in requests] == ["hr-callback"]
    assert requests[0]["mode"] == "callback"


def test_a_queued_request_carries_the_lead_a_strategist_would_pick_up(
    console_client: TestClient, store: InMemoryConversationStore
) -> None:
    """The card shows a name, a company, the Contact Details and the score, so the snapshot
    travels with the request: a queue that had to read the Lead per row would be a page of
    reads to draw one screen."""
    seed(store, CALLBACK)

    request = console_client.get(
        "/api/console/handovers", headers=as_strategist(ANGEL_TOKEN)
    ).json()["handovers"][0]

    assert request["state"] == "pending_strategist"
    assert request["session_id"] == "session-0001"
    assert request["lead"]["name"] == "Jane Doe"
    assert request["lead"]["email"] == "jane@example.com"
    assert request["lead"]["company"] == "Acme Manufacturing"
    assert request["lead"]["phone"] == "+1 555 0100"
    assert request["lead"]["score"] == 3
    assert request["lead"]["qualified"] is True
    # The five-name order the Console draws its ✓/— rows in, computed in code.
    assert request["lead"]["present_signals"] == [
        "industry_fit",
        "initiative_or_pain",
        "explicit_intent",
    ]
    assert request["created_at"] is not None


def test_the_request_detail_carries_the_lead_and_the_conversation_so_far(
    console_client: TestClient, store: InMemoryConversationStore
) -> None:
    """The Strategist joins informed, and the transcript is read here because a browser cannot
    read `sessions` — the rules deny it, and that is the point of them."""
    seed(store, CALLBACK)
    asyncio.run(store.append("session-0001", CONVERSATION))
    asyncio.run(
        store.upsert_lead(
            "session-0001",
            Lead(
                session_id="session-0001",
                name="Jane Doe",
                email="jane@example.com",
                phone="+1 555 0199",
                signals=dict(JANE.signals),
                score=3,
                qualified=True,
            ),
        )
    )

    response = console_client.get(
        "/api/console/handovers/hr-callback", headers=as_strategist(ANGEL_TOKEN)
    )

    assert response.status_code == 200
    detail = response.json()
    assert detail["handover"]["request_id"] == "hr-callback"
    assert detail["handover"]["prompt"] == "Do you want to jump into a call with our experts?"
    # The live Lead, not the snapshot: the Visitor corrected their phone number after the offer.
    assert detail["lead"]["phone"] == "+1 555 0199"
    assert detail["conversation"] == [
        {"role": "visitor", "text": "Supplier paperwork eats three days a week."},
        {"role": "assistant", "text": "That is exactly where agents earn back time."},
    ]


def test_the_conversation_leaves_out_the_tool_traffic_the_visitor_never_saw(
    console_client: TestClient, store: InMemoryConversationStore
) -> None:
    """ "Conversation so far" is what the two of them said. A `capture_lead` result read back
    as a chat bubble would show a Strategist a conversation that never happened."""
    seed(store, CALLBACK)
    asyncio.run(store.append("session-0001", CONVERSATION))

    detail = console_client.get(
        "/api/console/handovers/hr-callback", headers=as_strategist(ANGEL_TOKEN)
    ).json()

    assert [message["role"] for message in detail["conversation"]] == ["visitor", "assistant"]


def test_a_request_detail_falls_back_to_the_snapshot_when_the_session_has_no_lead(
    console_client: TestClient, store: InMemoryConversationStore
) -> None:
    """The snapshot is what the Assistant knew when it offered; it is never nothing."""
    seed(store, CALLBACK)

    detail = console_client.get(
        "/api/console/handovers/hr-callback", headers=as_strategist(ANGEL_TOKEN)
    ).json()

    assert detail["lead"]["name"] == "Jane Doe"
    assert detail["conversation"] == []


def test_a_handover_request_that_does_not_exist_is_not_found(console_client: TestClient) -> None:
    response = console_client.get(
        "/api/console/handovers/hr-nothing", headers=as_strategist(ANGEL_TOKEN)
    )

    assert response.status_code == 404


# --------------------------------------------------------------------- claim, join and end


def test_claiming_a_pending_video_request_puts_the_strategist_in_the_call(
    console_client: TestClient, store: InMemoryConversationStore
) -> None:
    """ "Claim & join call" is one button (docs/design §3.1), so it is one write: the two hops
    the machine names — `strategist_joined` then `in_call` — are validated and then persisted
    together, because `strategist_joined` is a moment nobody waits in and a queue that
    flickered through it would be showing a state that was never true for longer than a
    round trip."""
    seed(store, LIVE)

    response = console_client.post(
        "/api/console/handovers/hr-video/join", headers=as_strategist(ANGEL_TOKEN)
    )

    assert response.status_code == 200
    assert response.json()["state"] == "in_call"
    assert response.json()["room_url"] == ROOM_URL
    # The name the Visitor's panel says they are being assisted by — a person, not an account.
    assert response.json()["strategist_name"] == "Angel M."
    stored = asyncio.run(store.get_handover("hr-video"))
    assert stored is not None
    assert (stored.state, stored.strategist_name) == ("in_call", "Angel M.")


def test_ending_a_call_closes_the_handover_request(
    console_client: TestClient, store: InMemoryConversationStore
) -> None:
    seed(store, LIVE)
    console_client.post("/api/console/handovers/hr-video/join", headers=as_strategist(ANGEL_TOKEN))

    response = console_client.post(
        "/api/console/handovers/hr-video/end", headers=as_strategist(ANGEL_TOKEN)
    )

    assert response.status_code == 200
    assert response.json()["state"] == "ended"
    stored = asyncio.run(store.get_handover("hr-video"))
    assert stored is not None and stored.state == "ended"


def test_joining_a_request_that_is_already_in_a_call_is_refused(
    console_client: TestClient, store: InMemoryConversationStore
) -> None:
    """A second Strategist on a stale Console tab, or a double-clicked button. The state
    machine is the door (ADR-0007), whatever the browser believes."""
    seed(store, LIVE)
    console_client.post("/api/console/handovers/hr-video/join", headers=as_strategist(ANGEL_TOKEN))

    response = console_client.post(
        "/api/console/handovers/hr-video/join", headers=as_strategist(ANGEL_TOKEN)
    )

    assert response.status_code == 409


def test_joining_a_callback_is_refused_and_says_why(
    console_client: TestClient, store: InMemoryConversationStore
) -> None:
    """A Callback has no room to join: the Visitor was promised a phone call, and the button
    that would open a video call is not the one a Strategist should be able to press."""
    seed(store, CALLBACK)

    response = console_client.post(
        "/api/console/handovers/hr-callback/join", headers=as_strategist(ANGEL_TOKEN)
    )

    assert response.status_code == 409
    assert "Callback" in response.json()["detail"]


def test_ending_a_call_nobody_joined_is_refused(
    console_client: TestClient, store: InMemoryConversationStore
) -> None:
    seed(store, LIVE)

    response = console_client.post(
        "/api/console/handovers/hr-video/end", headers=as_strategist(ANGEL_TOKEN)
    )

    assert response.status_code == 409


def test_joining_a_request_that_does_not_exist_is_not_found(console_client: TestClient) -> None:
    response = console_client.post(
        "/api/console/handovers/hr-nothing/join", headers=as_strategist(ANGEL_TOKEN)
    )

    assert response.status_code == 404


def test_the_queue_carries_the_room_and_the_strategist_the_console_draws(
    console_client: TestClient, store: InMemoryConversationStore
) -> None:
    """The in-call banner shows the room URL and the queue card decides whether to draw
    "Claim & join call", so both travel on the row the Console already reads."""
    seed(store, LIVE)
    console_client.post("/api/console/handovers/hr-video/join", headers=as_strategist(ANGEL_TOKEN))

    request = console_client.get(
        "/api/console/handovers", headers=as_strategist(ANGEL_TOKEN)
    ).json()["handovers"][0]

    assert request["room_url"] == ROOM_URL
    assert request["strategist_name"] == "Angel M."


def test_joining_an_offer_the_visitor_has_not_answered_says_so_rather_than_calling_it_a_callback(
    console_client: TestClient, store: InMemoryConversationStore
) -> None:
    """A request with no mode is one nobody has agreed to anything on. Telling a Strategist it
    is a Callback would send them to phone a Visitor who has not asked to be phoned."""
    seed(store, UNANSWERED)

    response = console_client.post(
        "/api/console/handovers/hr-unanswered/join", headers=as_strategist(ANGEL_TOKEN)
    )

    assert response.status_code == 409
    assert "not been accepted yet" in response.json()["detail"]
    assert "Callback" not in response.json()["detail"]


def test_a_strategist_with_no_display_name_never_puts_their_email_in_front_of_the_visitor(
    console_client: TestClient, store: InMemoryConversationStore
) -> None:
    """`strategist_name` travels to the Visitor's panel. A Strategist's work address is not
    something a stranger on the internet gets because their Google profile has no name on it —
    the widget says "a Cadre strategist" instead, in the Visitor's own language."""
    seed(store, LIVE)

    response = console_client.post(
        "/api/console/handovers/hr-video/join", headers=as_strategist(NAMELESS_TOKEN)
    )

    assert response.status_code == 200
    assert response.json()["strategist_name"] == ""
    stored = asyncio.run(store.get_handover("hr-video"))
    assert stored is not None
    assert stored.strategist_name == ""
    assert "dana@example.com" not in response.text
