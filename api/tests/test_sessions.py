"""The Session cookie and the Turn cap — seam S1, stub provider and in-memory store.

A Session id is a capability: it is the key of the `ConversationStore` and, in production, a
Firestore document id. So the cookie is signed, and a cookie this service did not issue is not
a Session — it is a fresh one.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.session import SESSION_COOKIE, session_id_from_cookie, sign_session_id
from api.tests.conftest import COOKIE_SECRET, sse_events
from core.adapters.memory_store import InMemoryConversationStore
from core.adapters.stub_provider import StubModelProvider
from core.config import MissingConfigurationError, Settings
from core.provider import TextDelta, Usage
from core.turn import SESSION_CLOSED

# The cookie jar stores single-label hosts with `.local` appended, so a cookie planted by a
# test has to name the same domain the API's own `Set-Cookie` lands under.
COOKIE_DOMAIN = "testserver.local"

ANSWER = "Cadre AI is an AI strategy and implementation consultancy."
SPEND = Usage(input_tokens=12_400, output_tokens=48, cached_tokens=12_200, cost_usd=0.0031)


def stored_session_id(client: TestClient) -> str:
    """The id the store is keyed by, read back out of the signed cookie."""
    session_id = session_id_from_cookie(client.cookies[SESSION_COOKIE], COOKIE_SECRET)
    assert session_id is not None
    return session_id


def test_the_first_turn_issues_a_session_cookie_signed_by_this_service(
    client: TestClient, provider: StubModelProvider, store: InMemoryConversationStore
) -> None:
    provider.script("what does cadre", [TextDelta(ANSWER), SPEND])

    client.post("/api/chat", json={"message": "What does Cadre AI do?"})

    cookie = client.cookies[SESSION_COOKIE]
    session_id, _, signature = cookie.partition(".")
    assert signature, "the cookie carries a signature after the id"
    assert cookie == sign_session_id(session_id, COOKIE_SECRET)
    # The store is keyed by the id alone, never by the signed cookie value.
    assert asyncio.run(store.load(session_id))


def test_a_second_turn_with_the_cookie_continues_the_same_session(
    client: TestClient, provider: StubModelProvider, store: InMemoryConversationStore
) -> None:
    provider.script("hello", [TextDelta("Hi there."), SPEND])
    provider.script("and again", [TextDelta(ANSWER), SPEND])

    client.post("/api/chat", json={"message": "hello"})
    client.post("/api/chat", json={"message": "and again"})

    stored = asyncio.run(store.load(stored_session_id(client)))
    assert [message.content for message in stored] == ["hello", "Hi there.", "and again", ANSWER]


@pytest.mark.parametrize(
    ("label", "cookie"),
    [
        ("unsigned", "aaaaaaaaaaaaaaaaaaaaaaaa"),
        ("tampered signature", "aaaaaaaaaaaaaaaaaaaaaaaa.bm90LWEtc2lnbmF0dXJl"),
        ("malformed", "not a session at all"),
        ("empty", ""),
    ],
)
def test_a_cookie_this_service_did_not_issue_earns_a_fresh_session(
    client: TestClient,
    provider: StubModelProvider,
    store: InMemoryConversationStore,
    label: str,
    cookie: str,
) -> None:
    """A Session id names a conversation, so an unsigned id would let anyone read one."""
    provider.script("hello", [TextDelta("Hi there."), SPEND])
    # Domain and path match what the API sets, so the jar holds one cookie, not two.
    client.cookies.set(SESSION_COOKIE, cookie, domain=COOKIE_DOMAIN, path="/")

    client.post("/api/chat", json={"message": "hello"})

    issued = client.cookies[SESSION_COOKIE]
    assert issued != cookie, f"a {label} cookie must not be adopted as a Session"
    assert asyncio.run(store.load(stored_session_id(client)))
    # Nothing was written under the name the client offered.
    assert not asyncio.run(store.load(cookie.partition(".")[0]))


def test_a_cookie_carrying_a_raw_byte_earns_a_fresh_session_rather_than_a_500(
    client: TestClient, provider: StubModelProvider, store: InMemoryConversationStore
) -> None:
    """The signature half of the cookie is attacker-controlled bytes.

    A header decodes as latin-1, so one high byte makes the signature a non-ASCII string --
    which a constant-time comparison refuses outright. Left unchecked that is a 500 on every
    Turn, and because the cookie is only replaced on a response the browser never gets, the
    Visitor would resend the same broken cookie forever. It has to be an ordinary fresh
    Session. Sent as raw bytes because no cookie jar will encode this for us.
    """
    provider.script("hello", [TextDelta(ANSWER), SPEND])
    raw = "cadre_session=aaaaaaaaaaaaaaaaaaaaaaaa.s\u00edgnature".encode("latin-1")

    response = client.post("/api/chat", json={"message": "hello"}, headers={b"cookie": raw})

    assert response.status_code == 200
    assert asyncio.run(store.load(stored_session_id(client)))


def test_the_assistant_refuses_to_start_in_production_without_a_cookie_secret(
    web_dist: object,
) -> None:
    """An unsigned cookie in production is a guessable Session id, so this is fatal."""
    settings = Settings(env="production", session_cookie_secret="")

    with pytest.raises(MissingConfigurationError) as refusal:
        create_app(settings=settings, web_dist=web_dist)  # type: ignore[arg-type]

    assert "SESSION_COOKIE_SECRET" in str(refusal.value)


def test_a_session_at_its_turn_cap_is_closed_with_the_contact_path(
    capped_client: TestClient, provider: StubModelProvider
) -> None:
    provider.script("hello", [TextDelta("Hi there."), SPEND])

    capped_client.post("/api/chat", json={"message": "hello"})
    capped_client.post("/api/chat", json={"message": "hello"})
    response = capped_client.post("/api/chat", json={"message": "hello"})

    events = sse_events(response)
    assert [name for name, _ in events] == ["text", "done"]
    assert events[0] == ("text", {"delta": SESSION_CLOSED})
    assert "hello@gocadre.ai" in SESSION_CLOSED
    assert "cadreai.com/contact" in SESSION_CLOSED


def test_a_session_at_its_turn_cap_costs_nothing_and_stores_nothing(
    capped_client: TestClient, provider: StubModelProvider, store: InMemoryConversationStore
) -> None:
    provider.script("hello", [TextDelta("Hi there."), SPEND])
    capped_client.post("/api/chat", json={"message": "hello"})
    capped_client.post("/api/chat", json={"message": "hello"})

    capped_client.post("/api/chat", json={"message": "over the cap"})

    assert provider.calls == 2
    stored = asyncio.run(store.load(stored_session_id(capped_client)))
    assert [message.content for message in stored] == ["hello", "Hi there.", "hello", "Hi there."]
