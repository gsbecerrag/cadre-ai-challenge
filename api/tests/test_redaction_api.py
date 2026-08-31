"""The Refuse Set never reaches the provider, the store or a log line — seam S1.

One Turn is enough to show both Redaction Profiles doing different jobs: the Visitor pastes a
card and a work email, the card is masked everywhere and the email is kept as written for the
model and the Session (it is a Contact Detail, and collecting it is the product), while the
debug log body has the email tokenised as well (ADR-0006).
"""

import asyncio
import io
import json

import httpx2
from fastapi.testclient import TestClient

from api.session import SESSION_COOKIE, session_id_from_cookie
from api.tests.conftest import APP_LOGGER_PREFIX, COOKIE_SECRET, sse_events
from core.adapters.memory_store import InMemoryConversationStore
from core.adapters.stub_provider import StubModelProvider
from core.logging import configure_logging
from core.provider import TextDelta, Usage

# Luhn-valid and obviously fake: the card number the networks publish for testing.
CARD = "4111 1111 1111 1111"
MASKED_CARD = "**** **** **** 1111"
EMAIL = "jane@example.com"

PASTED = f"here is my card {CARD}, write me at {EMAIL}"
MASKED = f"here is my card {MASKED_CARD}, write me at {EMAIL}"
TOKENISED = f"here is my card {MASKED_CARD}, write me at [EMAIL_1]"

# What the model says back. It comes from the prompt's rule, not from the loop: nothing in
# the Turn hard-codes a refusal.
REPLY = "I don't need a card number — it isn't kept. What can I help you with?"
SPEND = Usage(input_tokens=13_100, output_tokens=24, cost_usd=0.0009)


def post_the_card(client: TestClient, provider: StubModelProvider) -> httpx2.Response:
    provider.script(MASKED_CARD, [TextDelta(REPLY), SPEND])
    return client.post("/api/chat", json={"message": PASTED})


def test_a_pasted_payment_card_reaches_the_provider_masked(
    client: TestClient, provider: StubModelProvider
) -> None:
    """Redaction happens before the provider call, so "never repeat it back" is a property of
    the pipeline rather than a rule the model has to remember."""
    post_the_card(client, provider)

    sent = provider.requests[-1].messages[-1]
    assert sent.content == MASKED
    assert CARD not in str(provider.requests)


def test_a_pasted_payment_card_is_stored_masked(
    client: TestClient, provider: StubModelProvider, store: InMemoryConversationStore
) -> None:
    """Same hook, before the write: what the Session holds is what the model saw."""
    post_the_card(client, provider)

    session_id = session_id_from_cookie(client.cookies[SESSION_COOKIE], COOKIE_SECRET)
    assert session_id is not None
    stored = asyncio.run(store.load(session_id))
    assert [message.content for message in stored] == [MASKED, REPLY]


def test_the_turn_result_carries_the_redaction_counts(
    client: TestClient, provider: StubModelProvider
) -> None:
    """The manifest is what ticket 06 tags the Trace with: categories and counts, no values."""
    response = post_the_card(client, provider)

    name, payload = sse_events(response)[-1]
    assert name == "done"
    assert payload["redactions"] == {"card": 1}


def test_a_turn_with_nothing_to_redact_says_nothing_about_redactions(
    client: TestClient, provider: StubModelProvider
) -> None:
    """The field is additive and optional, so a widget that has never heard of it is unaffected."""
    provider.script("hello", [TextDelta("Hi there."), SPEND])

    response = client.post("/api/chat", json={"message": "hello"})

    _name, payload = sse_events(response)[-1]
    assert "redactions" not in payload


def test_the_turns_debug_log_body_is_written_through_the_full_profile(
    client: TestClient, provider: StubModelProvider
) -> None:
    """Bodies are logged at debug level only and only after `full`: the card is already gone
    when the line is written, and the Visitor's email is tokenised on the way out."""
    stream = io.StringIO()
    configure_logging(level="DEBUG", stream=stream)

    post_the_card(client, provider)

    records = [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]
    bodies = [
        record["body"]
        for record in records
        if record["logger"].startswith(APP_LOGGER_PREFIX) and "body" in record
    ]
    assert bodies == [TOKENISED]
