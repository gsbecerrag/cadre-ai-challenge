"""Seam S2 — the metric logic, as pure functions over an Eval Case and a Turn result.

Nothing here runs a Turn, reaches a provider, or reads the Knowledge Base from disk. The Turn
results are literal event lists of the shape `POST /api/chat` streams, and the judge is a stub
whose verdict the test chose — so a failure here is a failure of the metric, never of the
Assistant. Whether the Assistant is right is what `evals/test_evals.py` and `make eval` ask.
"""

import asyncio
from collections.abc import Mapping, Sequence
from typing import Any

from core.knowledge import KBSection
from core.store import Lead
from evals.cases import EvalCase
from evals.judge import Verdict, parse_verdict
from evals.metrics import (
    TurnResult,
    correctness,
    escalation_correctness,
    groundedness,
    tool_correctness,
)

# Obviously fake Contact Details, as every fixture in this repository uses.
VISITOR_NAME = "Jane Rivera"
VISITOR_EMAIL = "jane@example.com"


class StubJudge:
    """A judge that returns the verdict the test chose, and counts how often it was asked."""

    def __init__(self, verdict: Verdict) -> None:
        self._verdict = verdict
        self.instructions: list[str] = []

    async def rule(self, instruction: str) -> Verdict:
        self.instructions.append(instruction)
        return self._verdict


def text(delta: str) -> tuple[str, Mapping[str, Any]]:
    return ("text", {"delta": delta})


def escalation(
    title: str, body: str = "", next_step: str = "Contact form", language: str = "en"
) -> tuple[str, Mapping[str, Any]]:
    return (
        "escalation",
        {
            "title": title,
            "body": body,
            "next_step": next_step,
            "citations": [],
            "language": language,
        },
    )


def tool(name: str) -> Sequence[tuple[str, Mapping[str, Any]]]:
    return [
        ("tool", {"name": name, "status": "started"}),
        ("tool", {"name": name, "status": "finished"}),
    ]


def trap_case(reason: str, forbidden: Sequence[str] = ()) -> EvalCase:
    return EvalCase(
        id="trap-fixture",
        kind="trap",
        language="en",
        messages=("What does the Intensive cost?",),
        validated=True,
        deterministic=True,
        expected_reason=reason,
        forbidden=tuple(forbidden),
    )


def qualification_case(
    expected_arguments: Mapping[str, str],
    expected_signals_present: Sequence[str],
    expected_score: int,
) -> EvalCase:
    return EvalCase(
        id="qualification-fixture",
        kind="qualification",
        language="en",
        messages=("I'm Jane Rivera, jane@example.com.",),
        validated=True,
        deterministic=True,
        expected_tool="capture_lead",
        expected_arguments=dict(expected_arguments),
        expected_signals_present=tuple(expected_signals_present),
        expected_score=expected_score,
    )


def in_kb_case(
    expected_sections: Sequence[str], golden_answer: str = "Cadre publishes nine industries."
) -> EvalCase:
    return EvalCase(
        id="in-kb-fixture",
        kind="in_kb",
        language="en",
        messages=("Which industries does Cadre serve?",),
        validated=True,
        golden_answer=golden_answer,
        expected_sections=tuple(expected_sections),
    )


def section(section_id: str, body: str) -> KBSection:
    topic, _, heading = section_id.partition("#")
    return KBSection(id=section_id, topic=topic, heading=heading, level=2, body=body)


# --- escalation_correctness (deterministic) ---------------------------------------------


def test_escalation_correctness_passes_on_the_expected_reasons_published_wording() -> None:
    result = TurnResult(events=(*tool("escalate"), escalation("Cadre doesn't publish pricing")))

    outcome = escalation_correctness(trap_case("pricing"), result)

    assert outcome.passed, outcome.reason


def test_escalation_correctness_fails_when_the_turn_raised_no_escalation() -> None:
    result = TurnResult(events=(text("The Intensive costs about $40,000."),))

    outcome = escalation_correctness(trap_case("pricing"), result)

    assert not outcome.passed
    assert "no Escalation" in outcome.reason


def test_escalation_correctness_fails_when_the_escalation_is_for_another_reason() -> None:
    result = TurnResult(events=(escalation("I can't compare Cadre with another firm"),))

    outcome = escalation_correctness(trap_case("pricing"), result)

    assert not outcome.passed
    assert "pricing" in outcome.reason


def test_escalation_correctness_reads_the_escalations_own_language() -> None:
    result = TurnResult(events=(escalation("Cadre no publica precios", language="es"),))

    outcome = escalation_correctness(trap_case("pricing"), result)

    assert outcome.passed, outcome.reason


def test_escalation_correctness_fails_when_a_forbidden_fact_reached_the_visitor_in_prose() -> None:
    result = TurnResult(
        events=(
            text("The Intensive is $40,000."),
            escalation("Cadre doesn't publish pricing"),
        )
    )

    outcome = escalation_correctness(trap_case("pricing", forbidden=["$40,000"]), result)

    assert not outcome.passed
    assert "$40,000" in outcome.reason


def test_escalation_correctness_fails_when_a_forbidden_fact_reached_the_escalation_body() -> None:
    result = TurnResult(
        events=(escalation("Cadre doesn't publish pricing", body="Engagements start at $40,000."),)
    )

    outcome = escalation_correctness(trap_case("pricing", forbidden=["$40,000"]), result)

    assert not outcome.passed


def test_escalation_correctness_matches_a_forbidden_fact_whatever_its_case() -> None:
    result = TurnResult(events=(text("Yes, Cadre is SOC 2 Certified."), escalation("x")))

    outcome = escalation_correctness(
        trap_case("certification", forbidden=["soc 2 certified"]), result
    )

    assert not outcome.passed


# --- tool_correctness (deterministic) ---------------------------------------------------


def test_tool_correctness_passes_on_the_expected_tool_contact_details_signals_and_score() -> None:
    lead = Lead(
        session_id="s1",
        name=VISITOR_NAME,
        email=VISITOR_EMAIL,
        signals={"industry_fit": "private equity", "explicit_intent": "wants to talk"},
        score=2,
    )
    result = TurnResult(events=tuple(tool("capture_lead")), lead=lead)

    outcome = tool_correctness(
        qualification_case({"name": VISITOR_NAME, "email": VISITOR_EMAIL}, ["industry_fit"], 2),
        result,
    )

    assert outcome.passed, outcome.reason


def test_tool_correctness_fails_when_the_expected_tool_was_never_called() -> None:
    result = TurnResult(events=(text("Nice to meet you."),), lead=None)

    outcome = tool_correctness(qualification_case({"name": VISITOR_NAME}, [], 0), result)

    assert not outcome.passed
    assert "capture_lead" in outcome.reason


def test_tool_correctness_fails_when_a_contact_detail_does_not_match() -> None:
    lead = Lead(session_id="s1", name="Someone Else", signals={}, score=0)
    result = TurnResult(events=tuple(tool("capture_lead")), lead=lead)

    outcome = tool_correctness(qualification_case({"name": VISITOR_NAME}, [], 0), result)

    assert not outcome.passed
    assert "name" in outcome.reason


def test_tool_correctness_fails_when_an_expected_qualification_signal_is_absent() -> None:
    lead = Lead(session_id="s1", name=VISITOR_NAME, signals={"industry_fit": "retail"}, score=1)
    result = TurnResult(events=tuple(tool("capture_lead")), lead=lead)

    outcome = tool_correctness(
        qualification_case({"name": VISITOR_NAME}, ["industry_fit", "timeline_or_budget"], 1),
        result,
    )

    assert not outcome.passed
    assert "timeline_or_budget" in outcome.reason


def test_tool_correctness_fails_when_the_qualification_score_is_not_the_expected_one() -> None:
    lead = Lead(session_id="s1", name=VISITOR_NAME, signals={"industry_fit": "retail"}, score=1)
    result = TurnResult(events=tuple(tool("capture_lead")), lead=lead)

    outcome = tool_correctness(
        qualification_case({"name": VISITOR_NAME}, ["industry_fit"], 3), result
    )

    assert not outcome.passed
    assert "3" in outcome.reason


def test_tool_correctness_recounts_the_score_from_the_signals_rather_than_trusting_the_lead() -> (
    None
):
    # A Lead whose stored score disagrees with its own signals is the bug ADR-0009 exists to
    # prevent: the score is counted in code, so the metric counts it again.
    lead = Lead(session_id="s1", name=VISITOR_NAME, signals={"industry_fit": "retail"}, score=3)
    result = TurnResult(events=tuple(tool("capture_lead")), lead=lead)

    outcome = tool_correctness(
        qualification_case({"name": VISITOR_NAME}, ["industry_fit"], 3), result
    )

    assert not outcome.passed


# --- correctness (judge, plus the deterministic citation check) -------------------------


def test_correctness_passes_when_a_section_is_cited_and_the_judge_agrees() -> None:
    result = TurnResult(events=(text("Nine industries. [industries#industries-cadre-serves]"),))
    judge = StubJudge(Verdict(passed=True, reason="same facts"))

    outcome = asyncio.run(
        correctness(in_kb_case(["industries#industries-cadre-serves"]), result, judge)
    )

    assert outcome.passed, outcome.reason
    assert len(judge.instructions) == 1


def test_correctness_fails_without_calling_the_judge_when_no_expected_section_is_cited() -> None:
    result = TurnResult(events=(text("Nine industries. [services#what-cadre-does]"),))
    judge = StubJudge(Verdict(passed=True, reason="same facts"))

    outcome = asyncio.run(
        correctness(in_kb_case(["industries#industries-cadre-serves"]), result, judge)
    )

    assert not outcome.passed
    assert "industries#industries-cadre-serves" in outcome.reason
    assert judge.instructions == []


def test_correctness_reports_the_judges_reason_when_the_judge_refuses_the_answer() -> None:
    result = TurnResult(events=(text("Four industries. [industries#industries-cadre-serves]"),))
    judge = StubJudge(Verdict(passed=False, reason="the count is wrong"))

    outcome = asyncio.run(
        correctness(in_kb_case(["industries#industries-cadre-serves"]), result, judge)
    )

    assert not outcome.passed
    assert "the count is wrong" in outcome.reason


# --- groundedness (judge, plus the deterministic citation check) ------------------------


def test_groundedness_passes_when_every_cited_section_resolves_and_the_judge_agrees() -> None:
    result = TurnResult(events=(text("Nine industries. [industries#industries-cadre-serves]"),))
    judge = StubJudge(Verdict(passed=True, reason="supported"))
    sections = {
        "industries#industries-cadre-serves": section("industries#industries-cadre-serves", "Nine.")
    }

    outcome = asyncio.run(groundedness(in_kb_case([]), result, judge, sections))

    assert outcome.passed, outcome.reason


def test_groundedness_fails_without_calling_the_judge_on_a_citation_that_does_not_resolve() -> None:
    result = TurnResult(events=(text("Nine industries. [industries#made-up-heading]"),))
    judge = StubJudge(Verdict(passed=True, reason="supported"))

    outcome = asyncio.run(groundedness(in_kb_case([]), result, judge, {}))

    assert not outcome.passed
    assert "industries#made-up-heading" in outcome.reason
    assert judge.instructions == []


def test_groundedness_gives_the_judge_the_body_of_every_cited_section() -> None:
    result = TurnResult(events=(text("Nine industries. [industries#industries-cadre-serves]"),))
    judge = StubJudge(Verdict(passed=True, reason="supported"))
    sections = {
        "industries#industries-cadre-serves": section(
            "industries#industries-cadre-serves", "Cadre AI publishes nine industries."
        )
    }

    asyncio.run(groundedness(in_kb_case([]), result, judge, sections))

    assert "Cadre AI publishes nine industries." in judge.instructions[0]


def test_groundedness_passes_when_the_turn_showed_the_visitor_nothing_to_ground() -> None:
    judge = StubJudge(Verdict(passed=False, reason="never asked"))

    outcome = asyncio.run(groundedness(in_kb_case([]), TurnResult(events=()), judge, {}))

    assert outcome.passed
    assert judge.instructions == []


def test_groundedness_judges_the_escalation_card_the_visitor_actually_read() -> None:
    result = TurnResult(
        events=(
            escalation(
                "Cadre doesn't publish pricing",
                body="The only published price is $5,000. [not-published#pricing]",
            ),
        )
    )
    judge = StubJudge(Verdict(passed=True, reason="supported"))
    sections = {"not-published#pricing": section("not-published#pricing", "$5,000 per firm.")}

    outcome = asyncio.run(groundedness(trap_case("pricing"), result, judge, sections))

    assert outcome.passed, outcome.reason
    assert "The only published price is $5,000." in judge.instructions[0]


# --- the judge's own JSON ---------------------------------------------------------------


def test_parse_verdict_reads_the_strict_json_the_prompt_asks_for() -> None:
    assert parse_verdict('{"pass": true, "reason": "the facts match"}') == Verdict(
        passed=True, reason="the facts match"
    )


def test_parse_verdict_reads_json_a_model_wrapped_in_a_code_fence() -> None:
    verdict = parse_verdict('```json\n{"pass": false, "reason": "invented a price"}\n```')

    assert verdict == Verdict(passed=False, reason="invented a price")


def test_parse_verdict_reads_json_a_model_buried_in_a_sentence() -> None:
    verdict = parse_verdict(
        'Here is my verdict: {"pass": true, "reason": "fine"} — hope that helps.'
    )

    assert verdict.passed


def test_parse_verdict_accepts_a_model_that_wrote_the_boolean_as_a_word() -> None:
    assert parse_verdict('{"pass": "yes", "reason": "fine"}').passed
    assert not parse_verdict('{"pass": "no", "reason": "invented"}').passed


def test_parse_verdict_fails_the_case_when_the_judge_returned_no_verdict_at_all() -> None:
    verdict = parse_verdict("I am not able to grade this.")

    assert not verdict.passed
    assert "I am not able to grade this." in verdict.reason


def test_parse_verdict_fails_the_case_when_the_judge_returned_broken_json() -> None:
    verdict = parse_verdict('{"pass": tru')

    assert not verdict.passed
