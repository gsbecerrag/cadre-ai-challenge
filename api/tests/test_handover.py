"""The Callback Hand-over, end to end through the API — seam S1.

The stub provider, the in-memory `ConversationStore` and the in-memory `Notifier`, so a whole
Qualified Lead → offer → accept → Callback flow runs with no network (constraint 4).

Two things are worth stating about what is tested here, because they are the decisions:

*The offer is a tool the model cannot always see.* The Assistant is never asked to remember
whether it has already offered a Hand-over or whether the Visitor scores highly enough — those
are facts about the Session, and a prompt that carried them would be a prompt that can be
argued with. So `offer_live_handover` is added to the tool definitions only when the Session's
Lead is a Qualified Lead and no Handover Request exists, and the tests read the tools the
provider was actually sent.

*Every transition is validated server-side.* The Visitor's browser posts to `accept` and
`decline`, so those endpoints are the door: a request another Session owns is a 404, and a move
the state machine does not allow is a 409, whatever the browser believes.

Every personal value here is obviously fake.
"""

import asyncio
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import api.handover
from api.main import create_app
from api.session import SESSION_COOKIE, session_id_from_cookie
from api.tests.conftest import COOKIE_SECRET, sse_events
from core.adapters.memory_notifier import InMemoryNotifier
from core.adapters.memory_store import InMemoryConversationStore
from core.adapters.recording_video import (
    FAKE_DOMAIN,
    BrokenVideoRooms,
    FailingVideoRooms,
    RecordingVideoRooms,
)
from core.adapters.stub_provider import StubModelProvider
from core.auth import StrategistIdentity
from core.config import Settings
from core.handover import DEFAULT_JOIN_TIMEOUT_SECONDS
from core.provider import ProviderRequest, TextDelta, ToolCall, Usage
from core.tools.offer_live_handover import OFFER_TOOL_NAME
from core.video import VideoRooms

SPEND = Usage(input_tokens=900, output_tokens=24, cached_tokens=800, cost_usd=0.0004)

ANGEL = StrategistIdentity(uid="uid-angel", email="angel@example.com", name="Angel M.")

# What the Assistant learned in one exchange: a job title and three of the five Qualification
# Signals — four, because the title is the "company size or role" signal as well (ADR-0009).
# Comfortably a Qualified Lead, with no name and no email yet, which is what makes the widget
# ask for them with the "Your details" card.
QUALIFYING_CAPTURE = ToolCall(
    id="call-1100",
    name="capture_lead",
    arguments={
        "role": "VP of Operations",
        "industry_fit": "Manufacturing & Logistics",
        "initiative_or_pain": "supplier paperwork eats three days a week",
        "explicit_intent": "wants to talk to someone about agents",
    },
)

# One signal short of the threshold, so the offer stays out of the model's reach.
THIN_CAPTURE = ToolCall(
    id="call-1101",
    name="capture_lead",
    arguments={"name": "Jane Doe", "industry_fit": "Manufacturing & Logistics"},
)

OFFER = ToolCall(
    id="call-1102",
    name=OFFER_TOOL_NAME,
    arguments={"prompt": "Do you want to jump into a call with our experts?"},
)

ClientFor = Callable[..., TestClient]


@pytest.fixture
def notifier() -> InMemoryNotifier:
    """The `Notifier` seam's test implementation: it records the Handover Requests it was told
    about, which is how "exactly one offer per Session" is asserted."""
    return InMemoryNotifier()


@pytest.fixture
def video() -> RecordingVideoRooms:
    """The `VideoRooms` seam's test implementation: it records the Handover Requests it was
    asked to open a room for, which is how "one room per video Hand-over and none for a
    Callback" is asserted at the place Daily.co would have been called (constraint 4)."""
    return RecordingVideoRooms()


@pytest.fixture
def build_client(
    settings: Settings,
    web_dist: Path,
    provider: StubModelProvider,
    store: InMemoryConversationStore,
    notifier: InMemoryNotifier,
    video: RecordingVideoRooms,
) -> Iterator[ClientFor]:
    """A chat client whose deployment either has the Live Hand-over flag on or does not."""
    clients: list[TestClient] = []

    def build(
        *,
        live_handover_enabled: bool = False,
        qualification_threshold: int = 3,
        video_rooms: VideoRooms | None = None,
        join_timeout_seconds: int = DEFAULT_JOIN_TIMEOUT_SECONDS,
    ) -> TestClient:
        configured = settings.model_copy(
            update={
                "live_handover_enabled": live_handover_enabled,
                "qualification_threshold": qualification_threshold,
                "handover_join_timeout_seconds": join_timeout_seconds,
            }
        )
        app = create_app(
            settings=configured,
            web_dist=web_dist,
            provider=provider,
            store=store,
            notifier=notifier,
            video_rooms=video if video_rooms is None else video_rooms,
        )
        client = TestClient(app, base_url="https://testserver")
        client.__enter__()
        clients.append(client)
        return client

    yield build
    for client in clients:
        client.__exit__(None, None, None)


@pytest.fixture
def client(build_client: ClientFor) -> TestClient:
    """The deployment the review runs on until ticket 15: the flag is off, so every accepted
    Hand-over is a Callback."""
    return build_client()


def session_id_of(client: TestClient) -> str:
    session_id = session_id_from_cookie(client.cookies[SESSION_COOKIE], COOKIE_SECRET)
    assert session_id is not None
    return session_id


def tools_offered(request: ProviderRequest) -> list[str]:
    """The tool names the model was actually sent on one provider call."""
    return [definition.name for definition in request.tools]


def qualify(client: TestClient, provider: StubModelProvider) -> None:
    """One Turn that makes the Session's Lead a Qualified Lead."""
    provider.script(
        "supplier paperwork",
        [QUALIFYING_CAPTURE],
        [TextDelta("That is exactly where agents earn back time."), SPEND],
    )
    client.post("/api/chat", json={"message": "Supplier paperwork eats three days a week."})


def offer(client: TestClient, provider: StubModelProvider) -> dict[str, Any]:
    """The Turn in which the Assistant offers the Hand-over. Returns the `offer` payload."""
    provider.script("talk to someone", [OFFER], [TextDelta("Let me know."), SPEND])
    response = client.post("/api/chat", json={"message": "Can I talk to someone?"})
    events = dict(sse_events(response))
    assert "offer" in events, [name for name, _ in sse_events(response)]
    return events["offer"]


def go_online(store: InMemoryConversationStore) -> None:
    asyncio.run(store.set_availability(ANGEL, True))


# --------------------------------------------------------------------- tool exposure


def test_the_offer_tool_is_out_of_reach_while_the_lead_is_below_the_threshold(
    client: TestClient, provider: StubModelProvider
) -> None:
    """A Hand-over spends a Strategist's time. Below the threshold the model is not asked to
    show restraint — it is not given the tool (ADR-0009)."""
    provider.script("we make parts", [THIN_CAPTURE], [TextDelta("Good to know."), SPEND])

    client.post("/api/chat", json={"message": "We make parts. I'm Jane."})

    assert OFFER_TOOL_NAME not in tools_offered(provider.requests[-1])
    assert "capture_lead" in tools_offered(provider.requests[-1])


def test_the_offer_tool_reaches_the_model_as_soon_as_the_lead_is_a_qualified_lead(
    client: TestClient, provider: StubModelProvider, store: InMemoryConversationStore
) -> None:
    """The tools are computed per provider call, so the Turn in which `capture_lead` takes the
    Lead over the threshold is the Turn in which the offer becomes available — a Visitor who
    asks to talk to someone in the same breath is not told to wait for the next Turn."""
    qualify(client, provider)

    lead = asyncio.run(store.get_lead(session_id_of(client)))
    assert lead is not None and lead.qualified is True
    assert OFFER_TOOL_NAME not in tools_offered(provider.requests[0])
    assert OFFER_TOOL_NAME in tools_offered(provider.requests[1])


def test_the_offer_tool_is_gone_again_once_one_offer_has_been_made_in_the_session(
    client: TestClient, provider: StubModelProvider
) -> None:
    """A Visitor asked twice is a Visitor being sold to. The Assistant is not trusted to
    remember: the tool is simply no longer there."""
    qualify(client, provider)
    offer(client, provider)

    assert OFFER_TOOL_NAME not in tools_offered(provider.requests[-1])


def test_a_qualified_lead_gets_exactly_one_hand_over_offer(
    client: TestClient, provider: StubModelProvider, notifier: InMemoryNotifier
) -> None:
    """The `Notifier` is what a Strategist hears, so "offered once" is asserted where the
    Console would have been told about it."""
    qualify(client, provider)
    first = offer(client, provider)

    # A model that calls the tool again anyway — a hallucinated name is answered, not obeyed.
    provider.script("please", [OFFER], [TextDelta("Of course."), SPEND])
    second = client.post("/api/chat", json={"message": "Please connect me."})

    assert [name for name, _ in sse_events(second)].count("offer") == 0
    assert len(notifier.created) == 1
    assert notifier.created[0].id == first["request_id"]
    assert notifier.created[0].state == "offered"
    assert notifier.created[0].lead.qualified is True


def test_the_offer_carries_the_request_and_the_line_the_assistant_phrased_it_with(
    client: TestClient, provider: StubModelProvider, store: InMemoryConversationStore
) -> None:
    qualify(client, provider)

    payload = offer(client, provider)

    assert payload["prompt"] == "Do you want to jump into a call with our experts?"
    stored = asyncio.run(store.get_handover(payload["request_id"]))
    assert stored is not None
    assert stored.state == "offered"
    assert stored.mode is None
    assert stored.session_id == session_id_of(client)
    # The Lead as it stood at the offer, so the Console's queue card is one read.
    assert stored.lead.role == "VP of Operations"
    assert stored.lead.score == 4


# --------------------------------------------------------------------- accept and decline


def test_accepting_with_nobody_online_creates_a_callback(
    client: TestClient, provider: StubModelProvider, store: InMemoryConversationStore
) -> None:
    """The fallback the whole feature rests on: a Visitor who says yes to an empty room is
    told a Strategist will call back, and the Lead is already captured (ADR-0007)."""
    qualify(client, provider)
    request_id = offer(client, provider)["request_id"]

    response = client.post(f"/api/handover/{request_id}/accept")

    assert response.status_code == 200
    assert response.json()["state"] == "pending_strategist"
    assert response.json()["mode"] == "callback"
    stored = asyncio.run(store.get_handover(request_id))
    assert stored is not None and stored.mode == "callback"


def test_accepting_with_a_strategist_online_and_the_flag_on_is_a_video_hand_over(
    build_client: ClientFor, provider: StubModelProvider, store: InMemoryConversationStore
) -> None:
    """Mode only: the Daily room is ticket 15. What this ticket decides is which of the two
    the Visitor is promised."""
    client = build_client(live_handover_enabled=True)
    go_online(store)
    qualify(client, provider)
    request_id = offer(client, provider)["request_id"]

    response = client.post(f"/api/handover/{request_id}/accept")

    assert response.json()["mode"] == "video"


def test_accepting_with_the_flag_off_is_a_callback_even_when_a_strategist_is_online(
    client: TestClient, provider: StubModelProvider, store: InMemoryConversationStore
) -> None:
    """`LIVE_HANDOVER_ENABLED=false` is how a video outage stops blocking lead capture: the
    Assistant degrades to Callbacks rather than promising a call it cannot open."""
    go_online(store)
    qualify(client, provider)
    request_id = offer(client, provider)["request_id"]

    response = client.post(f"/api/handover/{request_id}/accept")

    assert response.json()["mode"] == "callback"


def test_the_accept_response_carries_the_contact_details_the_callback_card_shows(
    client: TestClient, provider: StubModelProvider
) -> None:
    """The confirmation card reads back the details a Strategist will use. They are the
    Visitor's own, returned to the Session that gave them — nothing crosses a Session."""
    qualify(client, provider)
    request_id = offer(client, provider)["request_id"]

    body = client.post(f"/api/handover/{request_id}/accept").json()

    # Nothing but a role was captured, so the widget knows to ask for the rest.
    assert body["lead"] == {"name": "", "email": "", "company": ""}


def test_declining_an_offer_records_it_and_leaves_the_conversation_open(
    client: TestClient, provider: StubModelProvider, store: InMemoryConversationStore
) -> None:
    qualify(client, provider)
    request_id = offer(client, provider)["request_id"]

    response = client.post(f"/api/handover/{request_id}/decline")

    assert response.status_code == 200
    assert response.json()["state"] == "declined"
    assert response.json()["mode"] is None
    stored = asyncio.run(store.get_handover(request_id))
    assert stored is not None and stored.state == "declined"


def test_a_handover_request_another_session_owns_is_not_found(
    build_client: ClientFor, provider: StubModelProvider
) -> None:
    """The request id is in a URL. Holding it is not enough — the Session cookie has to own
    the request, or one Visitor could accept another's Hand-over."""
    visitor = build_client()
    qualify(visitor, provider)
    request_id = offer(visitor, provider)["request_id"]
    somebody_else = build_client()

    response = somebody_else.post(f"/api/handover/{request_id}/accept")

    assert response.status_code == 404


def test_a_handover_request_that_does_not_exist_is_not_found(client: TestClient) -> None:
    assert client.post("/api/handover/not-a-real-request/accept").status_code == 404


def test_accepting_the_same_offer_twice_is_refused_by_the_state_machine(
    client: TestClient, provider: StubModelProvider
) -> None:
    """A double-clicked button, a retried request, a stale tab. The second one is a 409, not a
    second Handover Request and not a silent success."""
    qualify(client, provider)
    request_id = offer(client, provider)["request_id"]
    client.post(f"/api/handover/{request_id}/accept")

    response = client.post(f"/api/handover/{request_id}/accept")

    assert response.status_code == 409


def test_declining_an_offer_that_was_already_accepted_is_refused(
    client: TestClient, provider: StubModelProvider
) -> None:
    qualify(client, provider)
    request_id = offer(client, provider)["request_id"]
    client.post(f"/api/handover/{request_id}/accept")

    response = client.post(f"/api/handover/{request_id}/decline")

    assert response.status_code == 409


# --------------------------------------------------------------------- the details card


def test_the_details_card_records_the_contact_details_the_visitor_typed(
    client: TestClient, provider: StubModelProvider, store: InMemoryConversationStore
) -> None:
    """The form card is the second path to a Lead (the design ruling): it goes through the
    same merge `capture_lead` uses, so one Session still has one Lead."""
    qualify(client, provider)

    response = client.post(
        "/api/leads",
        json={"name": "Jane Doe", "email": "jane@example.com", "company": "Acme Manufacturing"},
    )

    assert response.status_code == 200
    assert response.json()["lead"] == {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "company": "Acme Manufacturing",
    }
    lead = asyncio.run(store.get_lead(session_id_of(client)))
    assert lead is not None
    assert (lead.name, lead.email, lead.company) == (
        "Jane Doe",
        "jane@example.com",
        "Acme Manufacturing",
    )
    # The Qualification Signals are the Assistant's to learn, never the form's to change.
    assert lead.score == 4
    assert response.json()["score"] == 4
    assert lead.role == "VP of Operations"


def test_the_details_card_updates_the_handover_request_a_strategist_will_read(
    client: TestClient, provider: StubModelProvider, store: InMemoryConversationStore
) -> None:
    """The Visitor accepts, then types their name. Without this the Callback in the Console is
    a row with no name on it — the one thing the Strategist needs to make the call."""
    qualify(client, provider)
    request_id = offer(client, provider)["request_id"]
    client.post(f"/api/handover/{request_id}/accept")

    client.post("/api/leads", json={"name": "Jane Doe", "email": "jane@example.com"})

    stored = asyncio.run(store.get_handover(request_id))
    assert stored is not None
    assert stored.lead.name == "Jane Doe"
    assert stored.lead.email == "jane@example.com"
    # The state the accept left it in is untouched by a Contact Detail arriving.
    assert stored.state == "pending_strategist"


def test_the_details_card_scores_the_lead_against_the_configured_threshold(
    build_client: ClientFor, provider: StubModelProvider, store: InMemoryConversationStore
) -> None:
    """`qualified` is what unlocks the Hand-over offer, so the form path and the tool path have
    to answer the question the same way. This deployment asks for five signals; the Assistant
    learned four, so a Visitor typing their name into the card must not become a Qualified Lead
    on the way past — which is exactly what recomputing the flag at the built-in default would
    do."""
    client = build_client(qualification_threshold=5)
    qualify(client, provider)
    from_the_tool = asyncio.run(store.get_lead(session_id_of(client)))
    assert from_the_tool is not None and from_the_tool.qualified is False

    response = client.post("/api/leads", json={"name": "Jane Doe", "email": "jane@example.com"})

    assert response.json()["score"] == 4
    assert response.json()["qualified"] is False
    from_the_form = asyncio.run(store.get_lead(session_id_of(client)))
    assert from_the_form is not None and from_the_form.qualified is False


@pytest.mark.parametrize(
    "email",
    ["jane at example.com", "jane@example", "jane@", "@example.com", "jane@exam ple.com"],
    ids=["no-at", "no-dot-in-domain", "no-domain", "no-local-part", "space-in-domain"],
)
def test_the_details_card_refuses_a_work_email_nobody_could_reply_to(
    client: TestClient, provider: StubModelProvider, email: str
) -> None:
    """The whole point of the card is to give a Strategist a way back to the Visitor. An
    address that is not an address is a Callback that quietly cannot be returned, so it is
    refused at the door rather than stored and discovered a day later."""
    qualify(client, provider)

    response = client.post("/api/leads", json={"name": "Jane Doe", "email": email})

    assert response.status_code == 422


def test_the_details_card_needs_a_session_of_its_own(client: TestClient) -> None:
    """No Session cookie, no Lead: an anonymous POST would file Contact Details under a
    Session nobody is having a conversation in."""
    response = client.post(
        "/api/leads",
        json={"name": "Jane Doe", "email": "jane@example.com"},
    )

    assert response.status_code == 404


def test_a_details_card_with_nothing_in_it_is_refused(
    client: TestClient, provider: StubModelProvider
) -> None:
    qualify(client, provider)

    assert client.post("/api/leads", json={"name": " ", "email": ""}).status_code == 422


# --------------------------------------------------------------------- availability


def test_availability_tells_the_chat_header_whether_a_strategist_is_online(
    client: TestClient, store: InMemoryConversationStore
) -> None:
    """Public, because the chat panel is public and the header says which of the two lines to
    show. It answers one boolean about the team and names nobody."""
    assert client.get("/api/availability").json() == {"any_online": False}

    go_online(store)

    assert client.get("/api/availability").json() == {"any_online": True}


# --------------------------------------------------------------------- the video room


def test_accepting_in_video_mode_opens_exactly_one_room_and_stores_it_on_the_request(
    build_client: ClientFor,
    provider: StubModelProvider,
    store: InMemoryConversationStore,
    video: RecordingVideoRooms,
) -> None:
    """The room is created before the write and stored on the request in the same write, so
    the URL is already there when the widget asks for the Hand-over's status a moment later
    (ADR-0007). One room per Handover Request, and one only."""
    client = build_client(live_handover_enabled=True)
    go_online(store)
    qualify(client, provider)
    request_id = offer(client, provider)["request_id"]

    body = client.post(f"/api/handover/{request_id}/accept").json()

    assert video.requested == [request_id]
    assert body["mode"] == "video"
    assert body["room_url"] == f"https://{FAKE_DOMAIN}/cadre-{request_id.casefold()}"
    stored = asyncio.run(store.get_handover(request_id))
    assert stored is not None
    assert stored.room_url == body["room_url"]
    assert stored.room_expires_at is not None


def test_a_callback_hand_over_never_asks_for_a_room(
    client: TestClient,
    provider: StubModelProvider,
    video: RecordingVideoRooms,
) -> None:
    """Nobody is online, so the Visitor is promised a Callback. Paying a vendor for a room
    neither of them will ever open is the definition of a call that should not be made."""
    qualify(client, provider)
    request_id = offer(client, provider)["request_id"]

    body = client.post(f"/api/handover/{request_id}/accept").json()

    assert body["mode"] == "callback"
    assert body["room_url"] is None
    assert video.requested == []


def test_a_hand_over_degrades_to_a_callback_when_the_room_cannot_be_created(
    build_client: ClientFor,
    provider: StubModelProvider,
    store: InMemoryConversationStore,
) -> None:
    """A video outage must never block lead capture. The Visitor is told a Strategist will
    call back — with the Lead already captured — rather than shown an error for a room they
    never asked for by name."""
    failing = FailingVideoRooms()
    client = build_client(live_handover_enabled=True, video_rooms=failing)
    go_online(store)
    qualify(client, provider)
    request_id = offer(client, provider)["request_id"]

    response = client.post(f"/api/handover/{request_id}/accept")

    assert response.status_code == 200
    assert response.json()["mode"] == "callback"
    assert response.json()["room_url"] is None
    assert failing.requested == [request_id]
    stored = asyncio.run(store.get_handover(request_id))
    assert stored is not None
    assert (stored.state, stored.mode, stored.room_url) == ("pending_strategist", "callback", "")


def test_a_video_adapter_that_fails_in_an_unforeseen_way_still_yields_a_callback(
    build_client: ClientFor,
    provider: StubModelProvider,
    store: InMemoryConversationStore,
) -> None:
    """The acceptance is guarded against the adapter, not against one exception type.

    A `VideoRoomError` is the failure this code knows about; a `RuntimeError` out of a response
    that was not the JSON the vendor's documentation promised is the failure the next version of
    the adapter will have. Either way the Visitor pressed Yes, and losing that to a 500 loses
    the Lead — which is the one thing this feature may never do.
    """
    broken = BrokenVideoRooms()
    client = build_client(live_handover_enabled=True, video_rooms=broken)
    go_online(store)
    qualify(client, provider)
    request_id = offer(client, provider)["request_id"]

    response = client.post(f"/api/handover/{request_id}/accept")

    assert response.status_code == 200
    assert response.json()["mode"] == "callback"
    assert response.json()["room_url"] is None
    assert broken.requested == [request_id]


def test_with_the_flag_off_the_video_adapter_is_never_reached(
    client: TestClient,
    provider: StubModelProvider,
    store: InMemoryConversationStore,
    video: RecordingVideoRooms,
) -> None:
    """`LIVE_HANDOVER_ENABLED=false` is the whole path behaving as it did before ticket 15,
    with a Strategist online and everything: no room, no vendor call, a Callback."""
    go_online(store)
    qualify(client, provider)
    request_id = offer(client, provider)["request_id"]

    body = client.post(f"/api/handover/{request_id}/accept").json()

    assert body["mode"] == "callback"
    assert video.requested == []


def test_a_deployment_with_the_flag_off_needs_no_video_provider_at_all(
    settings: Settings,
    web_dist: Path,
    provider: StubModelProvider,
    store: InMemoryConversationStore,
) -> None:
    """Built with no video adapter passed in and no Daily key configured — CI, `make dev` and
    the deployed service until this ticket. It starts, and an acceptance is a Callback."""
    app = create_app(settings=settings, web_dist=web_dist, provider=provider, store=store)
    with TestClient(app, base_url="https://testserver") as client:
        go_online(store)
        qualify(client, provider)
        request_id = offer(client, provider)["request_id"]

        assert client.post(f"/api/handover/{request_id}/accept").json()["mode"] == "callback"


# --------------------------------------------------------------------- the status poll


def test_the_widget_reads_the_state_of_its_own_hand_over(
    build_client: ClientFor, provider: StubModelProvider, store: InMemoryConversationStore
) -> None:
    """The Visitor is watching a spinner, so the widget asks the server what happened rather
    than guessing. Same Session cookie, same ownership rule as accept and decline."""
    client = build_client(live_handover_enabled=True)
    go_online(store)
    qualify(client, provider)
    request_id = offer(client, provider)["request_id"]
    accepted = client.post(f"/api/handover/{request_id}/accept").json()

    response = client.get(f"/api/handover/{request_id}")

    assert response.status_code == 200
    assert response.json()["state"] == "pending_strategist"
    assert response.json()["mode"] == "video"
    assert response.json()["room_url"] == accepted["room_url"]
    assert response.json()["strategist_name"] is None


def test_the_status_names_the_strategist_once_one_has_joined(
    build_client: ClientFor, provider: StubModelProvider, store: InMemoryConversationStore
) -> None:
    """The panel says "You're being assisted by Angel M." (docs/design §2.6), so the name has
    to travel to the Visitor's side — and it is the Strategist's display name, because a
    Visitor is meeting a person and not an account."""
    client = build_client(live_handover_enabled=True)
    go_online(store)
    qualify(client, provider)
    request_id = offer(client, provider)["request_id"]
    client.post(f"/api/handover/{request_id}/accept")
    asyncio.run(store.update_handover(request_id, "strategist_joined", strategist_name="Angel M."))

    body = client.get(f"/api/handover/{request_id}").json()

    assert body["state"] == "strategist_joined"
    assert body["strategist_name"] == "Angel M."


def test_the_status_of_a_hand_over_another_session_owns_is_not_found(
    build_client: ClientFor, provider: StubModelProvider, store: InMemoryConversationStore
) -> None:
    """The status carries the room URL, and a room URL is the whole of the access control on
    a Daily call — so this read is guarded exactly as accept is."""
    client = build_client(live_handover_enabled=True)
    go_online(store)
    qualify(client, provider)
    request_id = offer(client, provider)["request_id"]
    client.post(f"/api/handover/{request_id}/accept")
    somebody_else = build_client(live_handover_enabled=True)

    assert somebody_else.get(f"/api/handover/{request_id}").status_code == 404


def test_a_video_hand_over_nobody_joined_becomes_a_callback_on_the_next_status_read(
    build_client: ClientFor,
    provider: StubModelProvider,
    store: InMemoryConversationStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The timeout is lazy and server-side: no scheduler, no second clock, just the question
    asked on the read the widget is already making. Past the window the Visitor is told a
    Strategist will call back, with the Lead already captured (ADR-0007)."""
    client = build_client(live_handover_enabled=True, join_timeout_seconds=120)
    go_online(store)
    qualify(client, provider)
    request_id = offer(client, provider)["request_id"]
    client.post(f"/api/handover/{request_id}/accept")
    monkeypatch.setattr(api.handover, "now", lambda: datetime.now(tz=UTC) + timedelta(seconds=121))

    body = client.get(f"/api/handover/{request_id}").json()

    assert body["state"] == "no_strategist_available"
    assert body["mode"] == "callback"
    stored = asyncio.run(store.get_handover(request_id))
    assert stored is not None
    assert (stored.state, stored.mode) == ("no_strategist_available", "callback")


def test_a_video_hand_over_still_inside_the_window_is_left_pending(
    build_client: ClientFor,
    provider: StubModelProvider,
    store: InMemoryConversationStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A Strategist reading the request before they claim it is the normal case."""
    client = build_client(live_handover_enabled=True, join_timeout_seconds=120)
    go_online(store)
    qualify(client, provider)
    request_id = offer(client, provider)["request_id"]
    client.post(f"/api/handover/{request_id}/accept")
    monkeypatch.setattr(api.handover, "now", lambda: datetime.now(tz=UTC) + timedelta(seconds=60))

    assert client.get(f"/api/handover/{request_id}").json()["state"] == "pending_strategist"


def test_a_callback_waiting_for_a_strategist_is_never_timed_out(
    client: TestClient,
    provider: StubModelProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A Callback is already the fallback: timing one out would take a call a Strategist still
    owes the Visitor away from them, hours after the tab was closed."""
    qualify(client, provider)
    request_id = offer(client, provider)["request_id"]
    client.post(f"/api/handover/{request_id}/accept")
    monkeypatch.setattr(api.handover, "now", lambda: datetime.now(tz=UTC) + timedelta(days=1))

    body = client.get(f"/api/handover/{request_id}").json()

    assert body["state"] == "pending_strategist"
    assert body["mode"] == "callback"
