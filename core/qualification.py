"""The Qualification Score: how many Qualification Signals a Lead carries.

The model extracts the signals and writes them into `capture_lead`'s arguments; the score is
counted here, in code (ADR-0009). That split is the whole point. A score the model assigns is
unauditable, drifts with the prompt, and cannot be unit-tested; a score counted in code is this
file plus a table of boundary cases, and the threshold that gates the Hand-over offer moves in
configuration rather than in a paragraph of English.

A signal is *present* when the Assistant put something in it. Anything else — an argument the
model left out, an empty string, a string of spaces — is absent, so a model filling every field
with `""` cannot manufacture a Qualified Lead.
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


def present_signals(signals: Mapping[str, str]) -> tuple[str, ...]:
    """The names of the Qualification Signals this Lead actually carries."""
    return tuple(name for name in SIGNAL_NAMES if str(signals.get(name, "") or "").strip())


def qualification_score(signals: Mapping[str, str]) -> int:
    """The Qualification Score: the count of Qualification Signals present, 0–5.

    Anything in the mapping that is not one of the five is ignored, so the Contact Details that
    travel with the signals in the same tool call never move the score.
    """
    return len(present_signals(signals))


def is_qualified(score: int, threshold: int = DEFAULT_QUALIFICATION_THRESHOLD) -> bool:
    """Whether a Lead with this score is a Qualified Lead — at or above the threshold."""
    return score >= threshold
