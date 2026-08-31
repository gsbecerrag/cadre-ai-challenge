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
import logging
import time
from collections.abc import Iterator
from typing import Any

import pytest

from core import redaction
from core.logging import configure_logging, get_logger, request_context

# Every logger `configure_logging` reaches into.
MANAGED_LOGGERS = ("", "cadre", "uvicorn", "uvicorn.error", "uvicorn.access")

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
# Ten digits that pass the cédula check digit by chance and are plainly phone numbers: one
# unformatted number in ten does, which is why the check digit alone cannot be the evidence.
COLOMBIAN_MOBILE = "3005550003"
US_NUMBER = "2125550000"
# Ten digits that fail it: labelled, so still an id, but not a cédula.
NOT_A_CEDULA = "2125551234"

# The longest Visitor message the chat endpoint accepts (`api.chat.MAX_MESSAGE_LENGTH`),
# and the budget one pass of a profile over it has. The budget is more than an order of
# magnitude above the linear cost (about 2.5ms) and far below anything a Visitor would
# notice. The fastest of a few passes is what is measured, because the failure being guarded
# against is a pattern that backtracks — deterministic, and three orders of magnitude over
# the budget — while a single wall-clock sample inside a full test run also picks up whatever
# else the machine was doing.
MAX_VISITOR_MESSAGE = 4000
REDACTION_BUDGET_MS = 50
REDACTION_PASSES = 3


@pytest.fixture(autouse=True)
def restored_logging() -> Iterator[None]:
    """`configure_logging` reaches into the process's loggers, so these tests put the state
    back. A `StringIO` handler left attached makes every later assertion about logging depend
    on the order the tests happened to run in."""
    saved = [
        (
            logging.getLogger(name),
            list(logging.getLogger(name).handlers),
            logging.getLogger(name).level,
            logging.getLogger(name).propagate,
            logging.getLogger(name).disabled,
        )
        for name in MANAGED_LOGGERS
    ]
    yield
    for logger, handlers, level, propagate, disabled in saved:
        logger.handlers = handlers
        logger.setLevel(level)
        logger.propagate = propagate
        logger.disabled = disabled


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


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("password: Hunter2", "password: [CREDENTIAL]"),
        ("clave = Hunter2", "clave = [CREDENTIAL]"),
        ("the OTP 482913 arrived", "the OTP [CREDENTIAL] arrived"),
        ("cvv 847", "cvv [CREDENTIAL]"),
    ],
)
def test_the_refuse_profile_still_tags_a_label_that_is_introducing_a_value(
    message: str, expected: str
) -> None:
    """Either an explicit separator or a value that looks like a code is enough; what is not
    enough is a label with an ordinary English word after it."""
    redacted = redaction.refuse(message)

    assert redacted.text == expected
    assert redacted.counts == {"credential": 1}


@pytest.mark.parametrize("message", [f"call me at {COLOMBIAN_MOBILE}", f"my number is {US_NUMBER}"])
def test_the_refuse_profile_leaves_an_unlabelled_ten_digit_number_alone(message: str) -> None:
    """`refuse` runs before the provider and before the store, so a phone number tagged as a
    cédula is a Contact Detail destroyed with no way back — and a cédula's check digit is one
    digit, which a tenth of unformatted phone numbers match by chance (ADR-0006: `refuse` does
    not touch Contact Details)."""
    redacted = redaction.refuse(message)

    assert redacted.text == message
    assert redacted.counts == {}


@pytest.mark.parametrize(
    "message",
    [f"mi cédula es {CEDULA}", f"CC {CEDULA}", f"C.C. {CEDULA}", f"cédula: {CEDULA}"],
)
def test_a_ten_digit_cedula_is_tagged_once_a_label_says_it_is_one(message: str) -> None:
    """The label is the evidence and the check digit is still the test: both have to hold."""
    redacted = redaction.refuse(message)

    assert redacted.text == message.replace(CEDULA, "[CEDULA]")
    assert redacted.counts == {"cedula": 1}


def test_a_labelled_number_that_fails_the_cedula_check_digit_is_not_a_cedula() -> None:
    """It is still an id by its label, so it is tagged as one — just not as a cédula."""
    redacted = redaction.refuse(f"CC {NOT_A_CEDULA}")

    assert redacted.text == "CC [GOV_ID]"
    assert redacted.counts == {"gov_id": 1}


def test_the_refuse_profile_reports_no_category_outside_the_refuse_set() -> None:
    """The profile's category list is what `run` is driven by, so this fails the day a rule
    that touches Contact Details is added without being gated on the profile."""
    redacted = redaction.refuse(
        f"card {CARD}, ssn {SSN}, password: Hunter2, mail {EMAIL}, call {PHONE}"
    )

    assert set(redacted.counts) <= set(redaction.REFUSE_SET)
    assert not set(redacted.counts) & set(redaction.CONTACT_DETAILS)


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
        # The brief's own data-security questions. A label is not a secret: what follows
        # "api key" here is the Visitor's question, not somebody's key.
        "how do you handle api key rotation for the agents you build?",
        "what is your password policy for the portal?",
        "our access token expires weekly",
        "the security code review is scheduled",
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


@pytest.mark.parametrize(
    "body",
    [
        pytest.param("1-" * (MAX_VISITOR_MESSAGE // 2), id="digits-and-hyphens"),
        pytest.param("a" * MAX_VISITOR_MESSAGE, id="one-long-word"),
        pytest.param("a." * (MAX_VISITOR_MESSAGE // 2), id="local-part-characters"),
        pytest.param("a" * (MAX_VISITOR_MESSAGE - 1) + "@", id="a-run-that-reaches-an-at-sign"),
        pytest.param("x dot " * (MAX_VISITOR_MESSAGE // 6), id="spoken-dots"),
    ],
)
def test_a_visitor_message_at_the_length_limit_is_redacted_in_milliseconds(body: str) -> None:
    """Both profiles run inline on the request thread — `refuse` before the provider call,
    `full` before every log line and every Trace — on a message the API accepts up to four
    thousand characters. So the cost has to stay linear in the length of the message: an
    email pattern that backtracks over a long run of local-part characters, or over a page of
    spoken-out `dot`s, turns a Visitor message into a stalled event loop, which is a denial of
    service and not a slow test."""
    elapsed_ms = []
    for _ in range(REDACTION_PASSES):
        started = time.perf_counter()
        redaction.full(body)
        elapsed_ms.append((time.perf_counter() - started) * 1000)

    assert min(elapsed_ms) < REDACTION_BUDGET_MS, f"redacting took {min(elapsed_ms):.0f}ms"


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


def test_a_nested_log_field_is_redacted_leaf_by_leaf() -> None:
    """A body does not stop being a body because it arrived inside a dict."""
    stream = io.StringIO()
    configure_logging(level="INFO", stream=stream)

    get_logger("turn").info(
        "Handover requested",
        extra={"lead": {"mail": EMAIL, "cards": [CARD], "score": 4}},
    )

    (record,) = _emitted(stream)
    assert record["lead"] == {"mail": "[EMAIL_1]", "cards": [MASKED_CARD], "score": 4}


def test_a_field_that_cannot_be_redacted_is_replaced_rather_than_written_raw() -> None:
    """A line is never dropped for the sake of one field, and the fallback is never the raw
    value: unredacted is the one outcome worse than losing the field."""
    stream = io.StringIO()
    configure_logging(level="INFO", stream=stream)
    cyclic: list[Any] = [EMAIL]
    cyclic.append(cyclic)

    get_logger("turn").info("Turn finished", extra={"body": cyclic})

    (record,) = _emitted(stream)
    assert record["message"] == "Turn finished"
    assert record["body"] == "[unredactable]"


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
