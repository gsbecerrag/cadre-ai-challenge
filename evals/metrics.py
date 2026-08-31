"""The four metrics, each a function of one Eval Case and the Turn it produced.

The Turn result is the parsed event list `POST /api/chat` streams, plus the Session's Lead read
back from the `ConversationStore` — because a tool call is not on the wire (the Visitor never
sees `capture_lead`), and what the tool actually wrote is the only honest evidence that it ran
correctly.

Two of the metrics are decided here and two are decided by the judge:

- `escalation_correctness` — deterministic. Did the Turn raise an Escalation carrying Cadre's
  published wording for the expected reason, and did no invented fact reach the Visitor?
- `tool_correctness` — deterministic. Was the expected tool called, does the Lead carry the
  Contact Details the Visitor gave, are the expected Qualification Signals present, and does the
  Qualification Score recounted from those signals match?
- `correctness` — the judge, plus a deterministic floor: at least one of the case's expected KB
  Sections must be cited before the judge is asked anything.
- `groundedness` — the judge, plus a deterministic floor: every id the answer cited must resolve
  against the compiled Knowledge Base. A citation to a section that does not exist is a
  fabricated citation, and no judge is needed to say so.

The deterministic floors run first and short-circuit, which is what keeps the CI subset free and
keeps a spent judge call from grading an answer that was already wrong.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from core.citations import split_citations
from core.knowledge import KBSection
from core.qualification import present_signals, qualification_score
from core.store import CONTACT_DETAIL_NAMES, Lead
from core.tools.escalate import ESCALATION_COPY, ESCALATION_REASONS, LANGUAGES, Language
from evals.cases import EvalCase
from evals.judge import Judge, correctness_instruction, groundedness_instruction

ESCALATION_CORRECTNESS = "escalation_correctness"
TOOL_CORRECTNESS = "tool_correctness"
CORRECTNESS = "correctness"
GROUNDEDNESS = "groundedness"

METRIC_NAMES: tuple[str, ...] = (
    CORRECTNESS,
    GROUNDEDNESS,
    ESCALATION_CORRECTNESS,
    TOOL_CORRECTNESS,
)

DEFAULT_LANGUAGE: Language = "en"


@dataclass(frozen=True)
class MetricOutcome:
    """One metric's ruling on one Eval Case, with the sentence that goes in the scorecard."""

    name: str
    passed: bool
    reason: str


@dataclass(frozen=True)
class TurnResult:
    """What the Assistant did with an Eval Case: the events the Visitor's browser received, and
    the Lead the Session ended with."""

    events: tuple[tuple[str, Mapping[str, Any]], ...] = ()
    lead: Lead | None = None
    turns: int = 1
    cost_usd: float = 0.0
    error: str = ""
    citation_markers: tuple[str, ...] = field(default_factory=tuple)

    @property
    def tool_names(self) -> tuple[str, ...]:
        return tuple(
            str(payload.get("name", ""))
            for name, payload in self.events
            if name == "tool" and payload.get("status") == "started"
        )

    @property
    def escalations(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(payload for name, payload in self.events if name == "escalation")

    @property
    def answer(self) -> str:
        """Everything the Visitor read, in the order they read it: the streamed prose, then each
        Escalation card and Walkthrough Card. Citation markers are left in — the judge is told
        to ignore them, and `visible_citations` needs them."""
        parts: list[str] = []
        for name, payload in self.events:
            if name == "text":
                parts.append(str(payload.get("delta", "")))
            elif name == "escalation":
                parts.append(
                    "\n{title}\n{body}\nNext step: {next_step}\n".format(
                        title=payload.get("title", ""),
                        body=payload.get("body", ""),
                        next_step=payload.get("next_step", ""),
                    )
                )
            elif name == "card":
                steps = " ".join(str(step) for step in payload.get("steps") or ())
                parts.append(f"\n{payload.get('title', '')}\n{steps}\n")
        return "".join(parts).strip()

    @property
    def citations(self) -> tuple[str, ...]:
        """Every KB Section the Turn cited: the markers left in the prose, and the ids the cards
        carry in their own `citations` field (a card's markers are lifted out server-side)."""
        _prose, markers = split_citations(self.answer)
        from_cards = tuple(
            str(section_id)
            for name, payload in self.events
            if name in ("escalation", "card")
            for section_id in payload.get("citations") or ()
        )
        return tuple(dict.fromkeys(markers + from_cards))


def escalation_correctness(case: EvalCase, result: TurnResult) -> MetricOutcome:
    """Did the Trap Question produce Cadre's published refusal, and nothing invented?

    The reason is read back off the card rather than out of the tool call, because the card is
    what the Visitor saw: `escalate` looks the title up by reason and language in one table
    (`core/tools/escalate.py`), so a title identifies the reason it was raised with. The two
    generic reasons share one wording and are therefore interchangeable here, which is honest —
    a Visitor cannot tell them apart either.
    """
    forbidden = _forbidden_hit(case.forbidden, result.answer)
    if forbidden:
        return MetricOutcome(
            ESCALATION_CORRECTNESS,
            passed=False,
            reason=f"an invented fact reached the Visitor: {forbidden!r}",
        )
    if not result.escalations:
        return MetricOutcome(
            ESCALATION_CORRECTNESS,
            passed=False,
            reason=f"no Escalation was raised; expected the {case.expected_reason!r} refusal",
        )
    raised = sorted({reason for card in result.escalations for reason in _reasons_of(card)})
    if case.expected_reason not in raised:
        return MetricOutcome(
            ESCALATION_CORRECTNESS,
            passed=False,
            reason=(
                f"expected the {case.expected_reason!r} refusal, "
                f"got {raised or ['wording that is in no copy table']}"
            ),
        )
    return MetricOutcome(
        ESCALATION_CORRECTNESS, passed=True, reason=f"escalated with {case.expected_reason!r}"
    )


def tool_correctness(case: EvalCase, result: TurnResult) -> MetricOutcome:
    """Was the expected tool called, and is the Lead it wrote the one the case describes?

    The Qualification Score is recounted here from the Lead's own signals rather than read off
    the Lead, so this fails if the number the Console shows ever stops being the count of the
    signals behind it (ADR-0009).
    """
    if case.expected_tool not in result.tool_names:
        return MetricOutcome(
            TOOL_CORRECTNESS,
            passed=False,
            reason=(
                f"{case.expected_tool!r} was never called; "
                f"called {list(result.tool_names) or 'nothing'}"
            ),
        )
    lead = result.lead
    if lead is None:
        return MetricOutcome(
            TOOL_CORRECTNESS, passed=False, reason="the Session ended with no Lead recorded"
        )

    wrong = [
        f"{name}={getattr(lead, name, '')!r} (expected {expected!r})"
        for name, expected in case.expected_arguments.items()
        if name in CONTACT_DETAIL_NAMES
        and _same_detail(str(getattr(lead, name, "")), expected) is False
    ]
    if wrong:
        return MetricOutcome(
            TOOL_CORRECTNESS,
            passed=False,
            reason="Contact Details do not match: " + ", ".join(wrong),
        )

    present = present_signals(lead.signals)
    missing = [name for name in case.expected_signals_present if name not in present]
    if missing:
        return MetricOutcome(
            TOOL_CORRECTNESS,
            passed=False,
            reason=f"Qualification Signals missing: {missing}; present {list(present)}",
        )

    counted = qualification_score(lead.signals)
    if counted != case.expected_score or lead.score != case.expected_score:
        return MetricOutcome(
            TOOL_CORRECTNESS,
            passed=False,
            reason=(
                f"expected a Qualification Score of {case.expected_score}; the Lead says "
                f"{lead.score} and its signals count to {counted}"
            ),
        )
    return MetricOutcome(
        TOOL_CORRECTNESS,
        passed=True,
        reason=f"{case.expected_tool} wrote a Lead scoring {counted} of 5",
    )


async def correctness(case: EvalCase, result: TurnResult, judge: Judge) -> MetricOutcome:
    """Does the answer say what the Knowledge Base says? Paraphrase is fine; a missing citation
    of the section the answer had to come from is not."""
    cited = set(result.citations)
    if case.expected_sections and not cited.intersection(case.expected_sections):
        return MetricOutcome(
            CORRECTNESS,
            passed=False,
            reason=(
                f"none of the expected KB Sections was cited: {list(case.expected_sections)}; "
                f"cited {sorted(cited) or 'nothing'}"
            ),
        )
    missing = [
        phrase for phrase in case.must_mention if phrase.casefold() not in result.answer.casefold()
    ]
    if missing:
        return MetricOutcome(
            CORRECTNESS, passed=False, reason=f"the answer never mentions {missing}"
        )
    verdict = await judge.rule(
        correctness_instruction(case.message, case.golden_answer, result.answer)
    )
    return MetricOutcome(CORRECTNESS, passed=verdict.passed, reason=verdict.reason)


async def groundedness(
    case: EvalCase,
    result: TurnResult,
    judge: Judge,
    sections: Mapping[str, KBSection],
) -> MetricOutcome:
    """Is every claim in the answer carried by the sections the answer cited?

    `case` is unused beyond its identity: groundedness is a property of an answer, not of an
    expectation, which is why every kind of Eval Case is judged on it.
    """
    answer = result.answer
    if not answer:
        return MetricOutcome(GROUNDEDNESS, passed=True, reason="the Turn made no claim")
    cited = result.citations
    unresolved = [section_id for section_id in cited if section_id not in sections]
    if unresolved:
        return MetricOutcome(
            GROUNDEDNESS,
            passed=False,
            reason=f"cited a KB Section that does not exist: {unresolved}",
        )
    verdict = await judge.rule(
        groundedness_instruction([sections[section_id] for section_id in cited], answer)
    )
    return MetricOutcome(GROUNDEDNESS, passed=verdict.passed, reason=verdict.reason)


def _same_detail(recorded: str, expected: str) -> bool:
    """Whether a Contact Detail on the Lead is the one the Visitor gave.

    Compared case-folded and with runs of whitespace collapsed. A Visitor who types their role
    in lower case and an Assistant that title-cases it on the way into the tool call have
    produced the same Lead — a Strategist calls that person either way — and a metric that
    failed on the capital D would be pinning one model's habits, not the tool contract. A
    different value is still a different value.
    """
    return " ".join(recorded.split()).casefold() == " ".join(expected.split()).casefold()


def _forbidden_hit(forbidden: Sequence[str], answer: str) -> str:
    haystack = answer.casefold()
    for phrase in forbidden:
        if phrase.casefold() in haystack:
            return phrase
    return ""


def _language_of(card: Mapping[str, Any]) -> Language:
    """The language an Escalation card was written in. Anything the card does not say, or says
    wrongly, reads as English — the same fallback `escalate` itself applies."""
    for language in LANGUAGES:
        if card.get("language") == language:
            return language
    return DEFAULT_LANGUAGE


def _reasons_of(card: Mapping[str, Any]) -> frozenset[str]:
    """Which `escalate` reasons this card's title could have come from, in its own language."""
    language = _language_of(card)
    title = str(card.get("title", ""))
    return frozenset(
        reason for reason in ESCALATION_REASONS if ESCALATION_COPY[reason][language].title == title
    )
