"""Seam S1: the Access Code gate on the endpoints that spend the model key (ticket 21)."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.access import ACCESS_CODE_REQUIRED, ACCESS_COOKIE, CODE_NOT_ACCEPTED, MAX_ATTEMPTS
from api.main import create_app
from core.adapters.memory_store import InMemoryConversationStore
from core.adapters.stub_provider import StubModelProvider
from core.config import Settings
from core.provider import TextDelta, Usage

# Obviously fake: the code the gated app below expects.
REVIEW_CODE = "review-pack-code-not-the-real-one"
ANSWER = "Cadre AI helps companies put AI to work [services#what-cadre-does]."
SPEND = Usage(input_tokens=10, output_tokens=5, cached_tokens=0, cost_usd=0.0001)
A_TURN = {"message": "What does Cadre AI do?"}
A_THUMB = {"trace_id": "trace-1", "rating": "down"}


@pytest.fixture
def gated_client(
    settings: Settings,
    web_dist: Path,
    provider: StubModelProvider,
    store: InMemoryConversationStore,
) -> Iterator[TestClient]:
    gated = settings.model_copy(update={"chat_access_code": REVIEW_CODE})
    app = create_app(settings=gated, web_dist=web_dist, provider=provider, store=store)
    with TestClient(app, base_url="https://testserver") as test_client:
        yield test_client


def test_with_no_code_configured_there_is_no_gate(
    client: TestClient, provider: StubModelProvider
) -> None:
    provider.script("what does cadre", [TextDelta(ANSWER), SPEND])

    assert client.get("/api/access").json() == {"required": False, "unlocked": True}
    assert client.post("/api/chat", json=A_TURN).status_code == 200


def test_a_gated_chat_refuses_a_turn_until_the_code_is_given(gated_client: TestClient) -> None:
    assert gated_client.get("/api/access").json() == {"required": True, "unlocked": False}

    response = gated_client.post("/api/chat", json=A_TURN)

    assert response.status_code == 401
    assert response.json() == {"detail": ACCESS_CODE_REQUIRED}
    assert ACCESS_COOKIE not in response.cookies


def test_the_right_code_unlocks_the_browser_and_a_turn_streams(
    gated_client: TestClient, provider: StubModelProvider
) -> None:
    provider.script("what does cadre", [TextDelta(ANSWER), SPEND])

    unlocked = gated_client.post("/api/access", json={"code": f"  {REVIEW_CODE}\n"})

    assert unlocked.status_code == 204
    set_cookie = unlocked.headers["set-cookie"]
    assert f"{ACCESS_COOKIE}=" in set_cookie
    assert "HttpOnly" in set_cookie and "Secure" in set_cookie
    assert gated_client.get("/api/access").json() == {"required": True, "unlocked": True}
    response = gated_client.post("/api/chat", json=A_TURN)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert ANSWER in response.text


def test_a_wrong_code_is_refused_without_a_cookie_or_a_reason(gated_client: TestClient) -> None:
    response = gated_client.post("/api/access", json={"code": "guess"})

    assert response.status_code == 401
    assert response.json() == {"detail": CODE_NOT_ACCEPTED}
    assert ACCESS_COOKIE not in response.cookies
    assert gated_client.post("/api/chat", json=A_TURN).status_code == 401


def test_a_forged_unlock_cookie_does_not_unlock(gated_client: TestClient) -> None:
    gated_client.cookies.set(ACCESS_COOKIE, "A" * 43)

    assert gated_client.get("/api/access").json()["unlocked"] is False
    assert gated_client.post("/api/chat", json=A_TURN).status_code == 401


def test_five_wrong_codes_lock_the_session_even_for_the_right_one(
    gated_client: TestClient,
) -> None:
    for _ in range(MAX_ATTEMPTS):
        assert gated_client.post("/api/access", json={"code": "guess"}).status_code == 401

    locked = gated_client.post("/api/access", json={"code": REVIEW_CODE})

    assert locked.status_code == 429
    assert gated_client.post("/api/chat", json=A_TURN).status_code == 401


def test_a_thumb_is_gated_too_because_it_spends_the_key(gated_client: TestClient) -> None:
    response = gated_client.post("/api/feedback", json=A_THUMB)

    assert response.status_code == 401
    assert response.json() == {"detail": ACCESS_CODE_REQUIRED}


def test_an_empty_code_is_a_validation_error_not_an_attempt(gated_client: TestClient) -> None:
    assert gated_client.post("/api/access", json={"code": "   "}).status_code == 422
