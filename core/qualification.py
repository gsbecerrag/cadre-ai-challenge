"""The Qualification Score: how many Qualification Signals a Lead carries.

The model extracts the signals and writes them into `capture_lead`'s arguments; the score is
counted here, in code (ADR-0009). That split is the whole point. A score the model assigns is
unauditable, drifts with the prompt, and cannot be unit-tested; a score counted in code is this
file plus a table of boundary cases, and the threshold that gates the Hand-over offer moves in
configuration rather than in a paragraph of English.

A signal is *present* when the Assistant actually learned something and put it in the argument.
Anything else is absent: an argument the model left out, an empty string, a string of spaces —
and the filler a model writes *instead* of omitting an optional field. "Not mentioned" is the
model saying it learned nothing, in the field meant for what it learned, and counting it would
put a Strategist in front of a Visitor who told us nothing. The prompt asks for omission; this
set is what makes the score independent of whether the prompt was obeyed.
"""

from collections.abc import Mapping

# The five Qualification Signals, in the order the Console shows them. These are also the
# argument names of `capture_lead`: the tool's schema and the score are the same five words.
SIGNAL_NAMES: tuple[str, ...] = (
    "industry_fit",
    "company_size_or_role",
    "initiative_or_pain",
    "timeline_or_budget",
    "explicit_intent",
)

MAX_QUALIFICATION_SCORE = len(SIGNAL_NAMES)

# ADR-0009: three of five unlocks the Hand-over offer. `QUALIFICATION_THRESHOLD` overrides it.
DEFAULT_QUALIFICATION_THRESHOLD = 3


# The ways a model says "I did not learn this" in a field that asked what it learned. Compared
# case-folded, after stripping, so `Not Provided` and `  unknown  ` are the same thing.
FILLER_VALUES: frozenset[str] = frozenset(
    {
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
    }
)


def learned(value: object) -> str:
    """What the Assistant actually learned in this argument, or an empty string.

    The one place the difference between "absent" and "filler" is decided, so the score, the
    Lead's stored signals and its Contact Details cannot disagree about it.
    """
    text = str(value if value is not None else "").strip()
    return "" if text.casefold() in FILLER_VALUES else text


def present_signals(signals: Mapping[str, str]) -> tuple[str, ...]:
    """The names of the Qualification Signals this Lead actually carries."""
    return tuple(name for name in SIGNAL_NAMES if learned(signals.get(name)))


def qualification_score(signals: Mapping[str, str]) -> int:
    """The Qualification Score: the count of Qualification Signals present, 0 to 5.

    Anything in the mapping that is not one of the five is ignored, so the Contact Details that
    travel with the signals in the same tool call never move the score.
    """
    return len(present_signals(signals))


def is_qualified(score: int, threshold: int = DEFAULT_QUALIFICATION_THRESHOLD) -> bool:
    """Whether a Lead with this score is a Qualified Lead — at or above the threshold."""
    return score >= threshold
