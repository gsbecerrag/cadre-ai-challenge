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
from core.tools.capture_lead import merged_lead

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


def test_filler_the_model_writes_instead_of_omitting_a_signal_is_not_present() -> None:
    """A model told to omit what it has not learned writes "not mentioned" into the field
    instead, routinely. Four of those must not read as four Qualification Signals: the score is
    what a Strategist is interrupted on, and "unknown" is not something anyone learned."""
    filler = {
        "industry_fit": "unknown",
        "company_size_or_role": "not mentioned",
        "initiative_or_pain": "N/A",
        "timeline_or_budget": "TBD",
    }

    assert qualification_score(filler) == 0
    assert qualification_score({**ALL_FIVE_SIGNALS, "timeline_or_budget": "None"}) == 4


@pytest.mark.parametrize(
    "filler",
    [
        "unknown",
        "n/a",
        "na",
        "none",
        "not mentioned",
        "not specified",
        "not provided",
        "tbd",
        "-",
        "?",
        "  Unknown  ",
        "Not Provided",
    ],
)
def test_no_spelling_of_i_did_not_learn_this_counts_as_a_qualification_signal(filler: str) -> None:
    assert qualification_score({"industry_fit": filler}) == 0


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


# `merged_lead` is the pure half of `capture_lead`: this call folded into the Session's Lead.
# It is unit-tested here rather than at S1 because both branches are about what a *sequence* of
# calls leaves behind, and the arithmetic of that is the score's arithmetic.


def test_a_later_call_that_says_nothing_new_does_not_erase_what_the_lead_already_holds() -> None:
    """The Assistant calls the tool again as details accumulate. A blank argument — or the
    filler a model writes in place of one — must keep what the Visitor already told us."""
    existing = merged_lead(
        None,
        "session-0900",
        {"email": "jane@example.com", "industry_fit": "Manufacturing & Logistics"},
    )

    updated = merged_lead(
        existing,
        "session-0900",
        {"email": "   ", "industry_fit": "unknown", "phone": "+1 555 0100"},
    )

    assert updated.email == "jane@example.com"
    assert updated.phone == "+1 555 0100"
    assert updated.signals == {"industry_fit": "Manufacturing & Logistics"}
    assert updated.score == 1


def test_a_later_call_that_learns_something_better_overrides_what_the_lead_held() -> None:
    existing = merged_lead(
        None,
        "session-0901",
        {"email": "jane@example.com", "role": "ops", "initiative_or_pain": "paperwork"},
    )

    updated = merged_lead(
        existing,
        "session-0901",
        {
            "role": "VP of Operations",
            "initiative_or_pain": "supplier paperwork eats three days a week",
        },
    )

    assert updated.role == "VP of Operations"
    assert updated.email == "jane@example.com"
    assert updated.signals["initiative_or_pain"] == "supplier paperwork eats three days a week"
    # Two: the initiative, and the role that came with the Contact Details (see below).
    assert updated.signals["company_size_or_role"] == "VP of Operations"
    assert updated.score == 2


def test_the_visitors_job_title_is_the_company_size_or_role_signal() -> None:
    """Carried from the evaluation suite (ticket 13): the Assistant reliably files a title in
    the `role` Contact Detail and then never repeats it as `company_size_or_role`, so a Visitor
    who says "I'm the COO" scored zero for a signal they had plainly given.

    The signal is "company size *or role*", and the role is right there on the Lead — so it is
    counted from the Contact Detail rather than waiting for the model to say it twice.
    """
    lead = merged_lead(None, "session-0902", {"role": "COO", "industry_fit": "Construction"})

    assert lead.signals["company_size_or_role"] == "COO"
    assert lead.score == 2


def test_a_size_the_assistant_learned_is_not_overwritten_by_the_job_title() -> None:
    """What the Assistant actually learned wins: "roughly 300 people, VP of Operations" is a
    better answer to the signal than the title on its own."""
    lead = merged_lead(
        None,
        "session-0903",
        {"role": "COO", "company_size_or_role": "roughly 300 people, reports to the CEO"},
    )

    assert lead.signals["company_size_or_role"] == "roughly 300 people, reports to the CEO"
    assert lead.score == 1
