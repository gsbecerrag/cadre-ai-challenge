"""The Qualification Score — seam S2.

The score is the count of Qualification Signals present on a Lead, computed in code and never
assigned by the model (ADR-0009). These are the boundaries the Hand-over offer gets gated on in
ticket 11, so they are pinned here rather than inferred from a conversation.
"""

import pytest

from core.qualification import (
    DEFAULT_QUALIFICATION_THRESHOLD,
    MAX_QUALIFICATION_SCORE,
    SIGNAL_NAMES,
    is_qualified,
    qualification_score,
)

# Obviously fake, and phrased the way the Assistant would report what it learned.
ALL_FIVE_SIGNALS = {
    "industry_fit": "Manufacturing & Logistics",
    "company_size_or_role": "VP of Operations, roughly 300 people",
    "initiative_or_pain": "supplier paperwork eats three days a week",
    "timeline_or_budget": "wants something running this quarter",
    "explicit_intent": "asked to speak to an AI strategist",
}


def first(count: int) -> dict[str, str]:
    """The first `count` Qualification Signals, so a score can be built to order."""
    return {name: ALL_FIVE_SIGNALS[name] for name in SIGNAL_NAMES[:count]}


def test_the_five_qualification_signals_are_the_ones_the_spec_names() -> None:
    """The names are the tool's argument names too: a rename here silently stops a signal
    counting, which is a Lead that scores lower than the conversation it came from."""
    assert SIGNAL_NAMES == (
        "industry_fit",
        "company_size_or_role",
        "initiative_or_pain",
        "timeline_or_budget",
        "explicit_intent",
    )
    assert MAX_QUALIFICATION_SCORE == 5


@pytest.mark.parametrize("count", [0, 1, 2, 3, 4, 5])
def test_the_score_is_the_count_of_qualification_signals_present(count: int) -> None:
    assert qualification_score(first(count)) == count


def test_a_signal_the_assistant_left_blank_or_whitespace_only_is_not_present() -> None:
    """A model that fills every argument with "" or " " must not score five out of five."""
    blank = dict.fromkeys(SIGNAL_NAMES, "")
    whitespace = dict.fromkeys(SIGNAL_NAMES, "   ")

    assert qualification_score(blank) == 0
    assert qualification_score(whitespace) == 0
    assert qualification_score({**ALL_FIVE_SIGNALS, "explicit_intent": "  "}) == 4


def test_an_argument_that_is_not_a_qualification_signal_does_not_count() -> None:
    """`capture_lead` carries Contact Details alongside the signals, and they do not score."""
    assert qualification_score({**first(2), "email": "jane@example.com", "name": "Jane"}) == 2


def test_a_lead_is_a_qualified_lead_only_at_or_above_the_threshold() -> None:
    threshold = DEFAULT_QUALIFICATION_THRESHOLD

    assert not is_qualified(0, threshold)
    assert not is_qualified(threshold - 1, threshold)
    assert is_qualified(threshold, threshold)
    assert is_qualified(MAX_QUALIFICATION_SCORE, threshold)


def test_the_threshold_defaults_to_three_signals() -> None:
    """Configuration (`QUALIFICATION_THRESHOLD`) moves it; the default is ADR-0009's three."""
    assert DEFAULT_QUALIFICATION_THRESHOLD == 3
    assert is_qualified(3)
    assert not is_qualified(2)
