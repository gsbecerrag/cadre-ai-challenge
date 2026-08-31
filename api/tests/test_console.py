"""The Strategist Console's endpoints — seam S1, with the `TokenVerifier` overridden.

Everything under `/api/console` shows or changes Cadre's side of the product: every Lead's raw
Contact Details, and the Availability that decides whether the Assistant may offer a Live
Hand-over at all. So the first three tests here are the door, not the features — a missing
token, a token the verifier rejects, and a real Google account that is simply not one of
Cadre's (ADR-0010).

The verifier is a seam because verifying a Firebase ID token is a network call to Google
(constraint 4); these tests script it instead, the same way the stub `ModelProvider` scripts
OpenRouter. The store is the in-memory one, so the presence documents and the Leads live and
die with the test.

Every personal value is obviously fake.
"""

import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from core.adapters.fake_verifier import ScriptedTokenVerifier
from core.adapters.memory_store import InMemoryConversationStore
from core.adapters.stub_provider import StubModelProvider
from core.auth import StrategistIdentity
from core.config import Settings
from core.store import Lead

# The Strategist Cadre employs, and a perfectly valid Google account that Cadre does not.
ANGEL = StrategistIdentity(uid="uid-angel", email="angel@example.com", name="Angel M.")
OUTSIDER = StrategistIdentity(uid="uid-outsider", email="outsider@example.com", name="Kim Outsider")
DANA = StrategistIdentity(uid="uid-dana", email="dana@example.com", name="Dana R.")

ANGEL_TOKEN = "id-token-angel"
OUTSIDER_TOKEN = "id-token-outsider"
DANA_TOKEN = "id-token-dana"

# Deliberately mixed case and padded: the allowlist a human types into a deploy command.
ALLOWED_EMAILS = " Angel@Example.com , dana@example.com "

CONSOLE_ENDPOINTS = (
    ("GET", "/api/console/leads"),
    ("GET", "/api/console/availability"),
)

FIRST_LEAD = Lead(
    session_id="session-0001",
    name="Jane Doe",
    email="jane@example.com",
    company="Acme Manufacturing",
    phone="+1 555 0100",
    role="VP of Operations",
    signals={
        "industry_fit": "Manufacturing & Logistics",
        "initiative_or_pain": "supplier paperwork eats three days a week",
        "timeline_or_budget": "wants something running this quarter",
    },
    score=3,
    qualified=True,
)

SECOND_LEAD = Lead(
    session_id="session-0002",
    name="Sam Roe",
    email="sam@example.com",
    company="Northwind Realty",
    role="Managing Partner",
    signals={"industry_fit": "Real Estate"},
    score=1,
    qualified=False,
)


@pytest.fixture
def verifier() -> ScriptedTokenVerifier:
    """Scripted per test: an ID token in, the Strategist it identifies out. Anything else is
    rejected, which is what an expired or forged token looks like from the API's side."""
    return ScriptedTokenVerifier({ANGEL_TOKEN: ANGEL, OUTSIDER_TOKEN: OUTSIDER, DANA_TOKEN: DANA})


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
    with TestClient(app, base_url="https://testserver") as test_client:
        yield test_client


def as_strategist(token: str) -> dict[str, str]:
    """The header the Console's browser sends: the Firebase ID token as a bearer credential."""
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize(("method", "path"), CONSOLE_ENDPOINTS)
def test_a_console_endpoint_refuses_a_request_with_no_token(
    console_client: TestClient, method: str, path: str
) -> None:
    """The Console is never open (ADR-0010): the deployed URL is public, so an endpoint that
    answered an anonymous request would publish every Lead's Contact Details."""
    response = console_client.request(method, path)

    assert response.status_code == 401


@pytest.mark.parametrize(("method", "path"), CONSOLE_ENDPOINTS)
def test_a_console_endpoint_refuses_a_token_the_verifier_rejects(
    console_client: TestClient, method: str, path: str
) -> None:
    """Expired, forged, or signed for another Firebase project — from here they are one case."""
    response = console_client.request(method, path, headers=as_strategist("not-a-real-token"))

    assert response.status_code == 401


@pytest.mark.parametrize(("method", "path"), CONSOLE_ENDPOINTS)
def test_a_console_endpoint_refuses_a_strategist_who_is_not_on_the_allowlist(
    console_client: TestClient, method: str, path: str
) -> None:
    """A genuine Google account that Cadre does not employ. 403, not 401: they signed in
    successfully and the message has to say so, or they will retry the sign-in forever."""
    response = console_client.request(method, path, headers=as_strategist(OUTSIDER_TOKEN))

    assert response.status_code == 403
    assert "outsider@example.com" in response.json()["detail"]


def test_a_bearer_scheme_is_required_so_a_bare_token_is_not_a_credential(
    console_client: TestClient,
) -> None:
    response = console_client.get("/api/console/leads", headers={"Authorization": ANGEL_TOKEN})

    assert response.status_code == 401


def test_an_allowlisted_strategist_sees_the_leads_newest_first(
    console_client: TestClient, store: InMemoryConversationStore
) -> None:
    """The Console's queue is a work list: the Lead that just arrived is the one a Strategist
    should see at the top, not the one from an hour ago."""
    asyncio.run(store.upsert_lead(FIRST_LEAD.session_id, FIRST_LEAD))
    asyncio.run(store.upsert_lead(SECOND_LEAD.session_id, SECOND_LEAD))

    response = console_client.get("/api/console/leads", headers=as_strategist(ANGEL_TOKEN))

    assert response.status_code == 200
    leads = response.json()["leads"]
    assert [lead["session_id"] for lead in leads] == ["session-0002", "session-0001"]


def test_a_lead_carries_its_contact_details_signals_and_the_score_counted_in_code(
    console_client: TestClient, store: InMemoryConversationStore
) -> None:
    """Raw Contact Details, deliberately (ADR-0006): a tokenised email is a Lead no Strategist
    can call back. `present_signals` is the five-name order the Console's rows are drawn in, so
    the browser never has to know which arguments of `capture_lead` are signals."""
    asyncio.run(store.upsert_lead(FIRST_LEAD.session_id, FIRST_LEAD))

    response = console_client.get("/api/console/leads", headers=as_strategist(ANGEL_TOKEN))

    lead = response.json()["leads"][0]
    assert lead["name"] == "Jane Doe"
    assert lead["email"] == "jane@example.com"
    assert lead["company"] == "Acme Manufacturing"
    assert lead["phone"] == "+1 555 0100"
    assert lead["role"] == "VP of Operations"
    assert lead["signals"] == dict(FIRST_LEAD.signals)
    assert lead["present_signals"] == [
        "industry_fit",
        "initiative_or_pain",
        "timeline_or_budget",
    ]
    assert lead["score"] == 3
    assert lead["qualified"] is True


def test_a_lead_updated_again_moves_back_to_the_top_of_the_console_list(
    console_client: TestClient, store: InMemoryConversationStore
) -> None:
    """Details arrive over several Turns. The Lead the Assistant just learned a phone number
    for is newer than the one it has not touched since, and the list has to agree."""
    asyncio.run(store.upsert_lead(FIRST_LEAD.session_id, FIRST_LEAD))
    asyncio.run(store.upsert_lead(SECOND_LEAD.session_id, SECOND_LEAD))
    asyncio.run(store.upsert_lead(FIRST_LEAD.session_id, FIRST_LEAD))

    response = console_client.get("/api/console/leads", headers=as_strategist(ANGEL_TOKEN))

    assert [lead["session_id"] for lead in response.json()["leads"]] == [
        "session-0001",
        "session-0002",
    ]


def test_a_strategist_starts_offline_and_nobody_is_available(console_client: TestClient) -> None:
    """Availability is a claim someone made in this session of the Console, not a default: an
    Assistant that offered a Live Hand-over because presence defaults to online would put a
    Qualified Lead in front of an empty room."""
    response = console_client.get("/api/console/availability", headers=as_strategist(ANGEL_TOKEN))

    assert response.status_code == 200
    assert response.json() == {"online": False, "any_online": False}


def test_going_online_records_the_strategists_availability_and_reports_it_back(
    console_client: TestClient,
) -> None:
    put = console_client.put(
        "/api/console/availability", json={"online": True}, headers=as_strategist(ANGEL_TOKEN)
    )

    assert put.status_code == 200
    assert put.json() == {"online": True, "any_online": True}
    read_back = console_client.get("/api/console/availability", headers=as_strategist(ANGEL_TOKEN))
    assert read_back.json() == {"online": True, "any_online": True}


def test_availability_reports_that_another_strategist_is_online_even_when_this_one_is_not(
    console_client: TestClient,
) -> None:
    """`any_online` is the signal the Assistant gates the Live Hand-over on, and it is about
    the team, not about whoever happens to have the Console open."""
    console_client.put(
        "/api/console/availability", json={"online": True}, headers=as_strategist(DANA_TOKEN)
    )

    response = console_client.get("/api/console/availability", headers=as_strategist(ANGEL_TOKEN))

    assert response.json() == {"online": False, "any_online": True}


def test_going_offline_takes_the_strategist_out_of_availability(
    console_client: TestClient,
) -> None:
    console_client.put(
        "/api/console/availability", json={"online": True}, headers=as_strategist(ANGEL_TOKEN)
    )

    response = console_client.put(
        "/api/console/availability", json={"online": False}, headers=as_strategist(ANGEL_TOKEN)
    )

    assert response.json() == {"online": False, "any_online": False}


def test_setting_availability_is_refused_for_a_strategist_who_is_not_on_the_allowlist(
    console_client: TestClient, store: InMemoryConversationStore
) -> None:
    """The write is behind the same door as the read: presence gates the Live Hand-over offer,
    so a stranger who could set it could summon Cadre's Strategists at will."""
    response = console_client.put(
        "/api/console/availability", json={"online": True}, headers=as_strategist(OUTSIDER_TOKEN)
    )

    assert response.status_code == 403
    assert asyncio.run(store.any_strategist_online()) is False
