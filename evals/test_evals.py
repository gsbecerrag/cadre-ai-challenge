"""Seam S5 — the evaluation suite: the Eval Cases themselves, and the subset CI can run free.

Two halves, and they are marked differently on purpose.

The well-formedness checks are unmarked, so `make check` runs them on every pull request: they
read `cases.jsonl` and the compiled Knowledge Base and nothing else, and they are what stops a
case file from rotting. An `expected_sections` id that no longer resolves, a `forbidden` string
that is actually a fact Cadre publishes, a Qualification Score that does not equal the count of
the signals beside it — each of those is a case that would pass or fail for the wrong reason,
and none of them needs a model to catch.

The case-driven half is marked `evals` and gated behind `--stub`, so it runs from
`make eval-stub` rather than from a bare `pytest`. It drives every deterministic Eval Case
through the whole application — `create_app`, the Turn loop, the tool registry, the
`ConversationStore` — with the stub `ModelProvider` scripted from the case itself. The scripted
response *is* the case's expected tool call, so this cannot tell anyone whether the Assistant
would have chosen it: what it guards is everything downstream of that choice. The escalate copy
table still has to produce Cadre's published refusal for the reason and the language; the Lead
still has to be merged and the Qualification Score still has to be counted in code; the events
still have to reach the browser in the shape the metrics read. And the prompt and the `escalate`
enum have to stay in lockstep, because a reason no longer in the enum is a case that stops
resolving here. Whether the *model* picks the right reason is what `make eval` asks, and that
costs money, which is why it is not this.
"""

import pytest

from core.adapters.knowledge_files import FileKnowledgeSource
from core.knowledge import compile_knowledge_base
from core.qualification import SIGNAL_NAMES, present_signals, qualification_score
from core.store import CONTACT_DETAIL_NAMES
from core.tools.escalate import ESCALATION_COPY, ESCALATION_REASONS, LANGUAGES
from evals.cases import EvalCase, deterministic_cases, load_cases
from evals.metrics import escalation_correctness, tool_correctness
from evals.runner import CAPTURE_LEAD, run_case_against_stub

CASES = load_cases()
DETERMINISTIC = deterministic_cases(CASES)

KB_SECTIONS = {
    section.id: section for section in compile_knowledge_base(FileKnowledgeSource().documents())
}
# Everything Cadre publishes, in one string: the KB Sections plus the escalate copy table,
# which is published wording that lives in code rather than in `knowledge/`.
PUBLISHED_TEXT = "\n".join(
    [section.body for section in KB_SECTIONS.values()]
    + [
        f"{copy.title}\n{copy.body}"
        for reason in ESCALATION_REASONS
        for language in LANGUAGES
        for copy in (ESCALATION_COPY[reason][language],)
    ]
).casefold()

EXPECTED_TOTAL = 50
MINIMUM_SPANISH_IN_KB = 4
INJECTION_RANGE = range(3, 5)


def test_the_suite_holds_fifty_eval_cases_in_the_three_kinds() -> None:
    kinds = [case.kind for case in CASES]

    assert len(CASES) == EXPECTED_TOTAL
    assert len({case.id for case in CASES}) == EXPECTED_TOTAL
    assert kinds.count("in_kb") == 20
    assert kinds.count("trap") == 20
    assert kinds.count("qualification") == 10


def test_the_suite_asks_in_spanish_as_well_as_english() -> None:
    spanish = [case for case in CASES if case.language == "es"]
    spanish_in_kb = [case for case in spanish if case.kind == "in_kb"]

    assert len(spanish_in_kb) >= MINIMUM_SPANISH_IN_KB
    assert {case.kind for case in spanish} == {"in_kb", "trap", "qualification"}


def test_the_suite_carries_the_prompt_injection_variants() -> None:
    injections = [case for case in CASES if case.injection]

    assert len(injections) in INJECTION_RANGE
    assert all(case.kind == "trap" for case in injections)


def test_every_trap_and_qualification_case_is_hand_validated_and_deterministic() -> None:
    checkable = [case for case in CASES if case.kind in ("trap", "qualification")]

    assert len(checkable) == 30
    assert all(case.validated for case in checkable), [
        case.id for case in checkable if not case.validated
    ]
    assert all(case.deterministic for case in checkable)
    assert not any(case.deterministic for case in CASES if case.kind == "in_kb")


def test_cases_are_well_formed() -> None:
    for case in CASES:
        assert case.messages, case.id
        assert all(message.strip() for message in case.messages), case.id
        if case.kind == "in_kb":
            assert case.golden_answer.strip(), case.id
            assert case.expected_sections, case.id
        if case.kind == "trap":
            assert case.expected_reason in ESCALATION_REASONS, case.id
            assert case.forbidden, case.id
        if case.kind == "qualification":
            assert case.expected_tool == CAPTURE_LEAD, case.id
            assert case.expected_arguments, case.id
            assert set(case.expected_arguments) <= set(CONTACT_DETAIL_NAMES), case.id
            assert set(case.expected_signals_present) <= set(SIGNAL_NAMES), case.id
            assert case.expected_score == len(case.expected_signals_present), case.id


def test_a_qualification_cases_stub_arguments_produce_exactly_its_expectation() -> None:
    """The scripted `capture_lead` call has to be the case's own expectation, or the CI subset
    is grading something the case file never claimed."""
    for case in CASES:
        if case.kind != "qualification":
            continue
        assert case.stub_arguments, case.id
        for name, value in case.expected_arguments.items():
            assert case.stub_arguments.get(name) == value, f"{case.id}: {name}"
        assert present_signals(case.stub_arguments) == case.expected_signals_present, case.id
        assert qualification_score(case.stub_arguments) == case.expected_score, case.id


def test_every_expected_section_resolves() -> None:
    unresolved = {
        case.id: [
            section_id for section_id in case.expected_sections if section_id not in KB_SECTIONS
        ]
        for case in CASES
    }

    assert not {case_id: missing for case_id, missing in unresolved.items() if missing}


def test_no_forbidden_string_is_something_cadre_actually_publishes() -> None:
    """A `forbidden` string stands for an invented fact. If Cadre publishes it — in a KB Section
    or in the escalate copy table — then the Assistant saying it is honest, and the case would
    fail an Assistant that did its job."""
    published = {
        case.id: [phrase for phrase in case.forbidden if phrase.casefold() in PUBLISHED_TEXT]
        for case in CASES
    }

    assert not {case_id: phrases for case_id, phrases in published.items() if phrases}


@pytest.mark.evals
@pytest.mark.parametrize("case", DETERMINISTIC, ids=[case.id for case in DETERMINISTIC])
def test_a_deterministic_eval_case_passes_its_metrics(case: EvalCase) -> None:
    result = run_case_against_stub(case)

    outcome = (
        escalation_correctness(case, result)
        if case.kind == "trap"
        else tool_correctness(case, result)
    )

    assert outcome.passed, f"{case.id}: {outcome.reason}"
