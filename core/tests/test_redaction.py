"""Both Redaction Profiles against the catalog's validated formats — seam S2.

Every value here is obviously fake: the payment-card fixtures are the test numbers the card
networks publish for exactly this purpose, and the ids are check-digit-valid inventions. Two
of the skill catalog's own illustrations do not pass the validators it documents (its example
card fails Luhn, its example cédula fails the check digit), so the fixtures below are the same
shapes with the check digit corrected — a redactor tested against a value its own validator
rejects proves nothing.
"""

import io
import json
from typing import Any

import pytest

from core import redaction
from core.logging import configure_logging, get_logger, request_context

# Luhn-valid, and the most obviously fake card number in existence.
CARD = "4111 1111 1111 1111"
MASKED_CARD = "**** **** **** 1111"
# The same sixteen digits with the check digit off by one: an order number, not a card.
NOT_A_CARD = "4111 1111 1111 1112"
SSN = "123-45-6789"
CEDULA = "1712345675"
RUC = "1712345675001"
CPF = "111.444.777-35"
DNI = "12345678Z"
COLOMBIAN_CEDULA = "79.123.456"
IBAN = "ES91 2100 0418 4502 0005 1332"
EMAIL = "jane@example.com"
OTHER_EMAIL = "rob@example.com"
PHONE = "+1 555 0100"


def test_the_refuse_profile_masks_a_payment_card_to_its_last_four() -> None:
    """Last four is the industry's own reference form: the conversation can still say which
    card without the number being usable by anyone who reads the Session afterwards."""
    redacted = redaction.refuse(f"here is my card {CARD} for the invoice")

    assert redacted.text == f"here is my card {MASKED_CARD} for the invoice"
    assert redacted.counts == {"card": 1}


def test_the_refuse_profile_leaves_a_number_that_fails_luhn_where_it_is() -> None:
    """Validation is why this can run on every Turn: sixteen digits that fail the checksum are
    an order or a tracking number, and eating those would make the Assistant useless."""
    text = f"order {NOT_A_CARD} shipped 2026-08-30, total $45,000"

    redacted = redaction.refuse(text)

    assert redacted.text == text
    assert redacted.counts == {}


def test_the_refuse_profile_masks_an_iban_to_its_last_four() -> None:
    redacted = redaction.refuse(f"our IBAN is {IBAN}")

    assert redacted.text == "our IBAN is ****1332"
    assert redacted.counts == {"iban": 1}


@pytest.mark.parametrize(
    ("message", "expected", "category"),
    [
        (f"my SSN is {SSN}", "my SSN is [SSN]", "ssn"),
        (f"mi cédula es {CEDULA}", "mi cédula es [CEDULA]", "cedula"),
        (f"mi RUC es {RUC}", "mi RUC es [RUC]", "ruc"),
        (f"CPF {CPF}", "CPF [GOV_ID]", "gov_id"),
        (f"DNI {DNI}", "DNI [GOV_ID]", "gov_id"),
        (
            f"cédula de ciudadanía {COLOMBIAN_CEDULA}",
            "cédula de ciudadanía [GOV_ID]",
            "gov_id",
        ),
    ],
)
def test_the_refuse_profile_replaces_a_government_id_with_a_typed_tag(
    message: str, expected: str, category: str
) -> None:
    """A government id has no safe partial form — a fragment still narrows to one person — so
    the digits go entirely and only the type survives."""
    redacted = redaction.refuse(message)

    assert redacted.text == expected
    assert redacted.counts == {category: 1}


def test_the_refuse_profile_replaces_a_labelled_credential_with_a_typed_tag() -> None:
    redacted = redaction.refuse("my password is Hunter2 and the verification code is 482913")

    assert redacted.text == "my password is [CREDENTIAL] and the verification code is [CREDENTIAL]"
    assert redacted.counts == {"credential": 2}


def test_the_refuse_profile_tags_a_sensitive_category_the_visitor_states_about_themselves() -> None:
    redacted = redaction.refuse("my diagnosis is type 2 diabetes, can Cadre help with that?")

    assert redacted.text == "my diagnosis is [SENSITIVE], can Cadre help with that?"
    assert redacted.counts == {"sensitive": 1}


@pytest.mark.parametrize(
    "message",
    [
        # The words this product actually trades in. A redactor that eats them is worse than
        # no redactor: it corrupts the message the model has to answer.
        "our token budget is 200000 tokens a month",
        "el factor clave es la velocidad de respuesta",
        "our diagnosis workflow triages support tickets with AI",
        "invoice INV-100234 for $420,000, dated 2026-08-31",
        "we are a team of 45 in Quito and we ship on 2026-09-15",
    ],
)
def test_the_refuse_profile_leaves_ordinary_business_text_alone(message: str) -> None:
    redacted = redaction.refuse(message)

    assert redacted.text == message
    assert redacted.counts == {}


def test_the_refuse_profile_leaves_contact_details_where_the_visitor_wrote_them() -> None:
    """Contact Details are what this product exists to collect (ADR-0006): a work email and a
    phone number are the Lead, not a leak."""
    text = f"I run ops at Acme — write to {EMAIL} or call {PHONE}"

    redacted = redaction.refuse(text)

    assert redacted.text == text
    assert redacted.counts == {}


def test_the_full_profile_tokenises_contact_details_consistently_within_one_text() -> None:
    """One value, one token: a Trace or a log line stays readable enough to debug, and two
    mentions of the same person do not read as two people."""
    redacted = redaction.full(
        f"write to {EMAIL}, copy {OTHER_EMAIL}, {EMAIL} again — or call {PHONE} or {PHONE}"
    )

    assert redacted.text == (
        "write to [EMAIL_1], copy [EMAIL_2], [EMAIL_1] again — or call [PHONE_1] or [PHONE_1]"
    )
    assert redacted.counts == {"email": 2, "phone": 1}


def test_the_full_profile_strips_the_refuse_set_as_well_as_the_contact_details() -> None:
    redacted = redaction.full(f"card {CARD}, ssn {SSN}, mail {EMAIL}")

    assert redacted.text == f"card {MASKED_CARD}, ssn [SSN], mail [EMAIL_1]"
    assert redacted.counts == {"card": 1, "ssn": 1, "email": 1}


def test_the_counts_are_a_manifest_of_categories_and_carry_no_values() -> None:
    """The counts ride along to the Trace (ticket 06), so "how often do Visitors paste things
    they should not" is a number nobody has to read a conversation to get."""
    redacted = redaction.refuse(f"one card {CARD}, another card {CARD}, and my SSN {SSN}")

    assert redacted.counts == {"card": 2, "ssn": 1}


def _emitted(stream: io.StringIO) -> list[dict[str, Any]]:
    return [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]


def test_a_debug_log_body_is_written_through_the_full_profile() -> None:
    """Bodies are logged at debug level only, and only after `full` (spec, ADR-0006). The
    Refuse Set is already gone by the time a Turn logs anything; what `full` adds here is the
    Contact Details, which Cloud Logging has no business holding."""
    stream = io.StringIO()
    configure_logging(level="DEBUG", stream=stream)

    get_logger("turn").debug(
        "Visitor message",
        extra={"body": f"card {CARD}, mail {EMAIL}, call {PHONE}"},
    )

    (record,) = _emitted(stream)
    assert record["body"] == f"card {MASKED_CARD}, mail [EMAIL_1], call [PHONE_1]"


def test_a_log_message_is_a_body_too() -> None:
    """A line written by a library, or a provider's own error text, is as capable of carrying
    a Visitor's email as a field we chose to log."""
    stream = io.StringIO()
    configure_logging(level="INFO", stream=stream)

    get_logger("turn").warning(f"upstream refused the Turn for {EMAIL}")

    (record,) = _emitted(stream)
    assert record["message"] == "upstream refused the Turn for [EMAIL_1]"


def test_the_correlation_ids_are_not_bodies_and_survive_intact() -> None:
    """A request id is thirty-two hex characters, which is exactly the shape of an API key.
    Redacting it would leave a request's lines unjoinable, which is the point of having it."""
    stream = io.StringIO()
    configure_logging(level="INFO", stream=stream)
    hex_request_id = "a" * 32

    with request_context(request_id=hex_request_id, session_id="sess-0100"):
        get_logger("turn").info("Turn finished")

    (record,) = _emitted(stream)
    assert record["request_id"] == hex_request_id
    assert record["session_id"] == "sess-0100"
