"""One Eval Case, and the JSONL file that holds all fifty of them.

An Eval Case is a Visitor message (or a short exchange), the expected Assistant behaviour, and
the metric that judges it (CONTEXT.md). Three kinds, because the expectation has three shapes:

- `in_kb` — the Knowledge Base answers it. The case carries a golden answer drafted from
  `knowledge/*.md` and the KB Section ids the answer must cite. Judged by `correctness` and
  `groundedness`.
- `trap` — a Trap Question: it sounds answerable and the answer is not in the Knowledge Base.
  The case carries the `escalate` reason that fits and the strings that would be an invented
  fact if the Visitor ever read them. Judged by `escalation_correctness`.
- `qualification` — the Visitor shares Contact Details. The case carries the tool that must be
  called, the Contact Details it must carry, the Qualification Signals that must be present and
  the Qualification Score they add up to. Judged by `tool_correctness`.

`deterministic` marks the cases the CI subset runs: every trap and qualification case, because
their expectations are checkable without a model. `validated` records that a human read the
case against the Knowledge Base and stands behind it (ADR-0008).

The file is JSONL rather than one JSON document so that a case is one line: the Triage Agent
proposes new cases in this shape (ADR-0005), and a one-line addition is a reviewable diff.
"""

import json
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, get_args

CASES_FILE = Path(__file__).resolve().parent / "cases.jsonl"

Kind = Literal["in_kb", "trap", "qualification"]
Language = Literal["en", "es"]

KINDS: tuple[Kind, ...] = get_args(Kind)
LANGUAGES: tuple[Language, ...] = get_args(Language)


class MalformedCaseError(ValueError):
    """A line in the JSONL that is not an Eval Case. Loud, because a case nobody can parse is a
    case nobody is running, and a silently skipped Trap Question is worse than none at all."""


@dataclass(frozen=True)
class EvalCase:
    """One scenario in the evaluation suite."""

    id: str
    kind: Kind
    language: Language
    # One message for a single-Turn case, several for a qualification exchange. The Assistant
    # answers each in the same Session, in order.
    messages: tuple[str, ...]
    validated: bool
    deterministic: bool = False

    # --- in_kb ---
    golden_answer: str = ""
    expected_sections: tuple[str, ...] = ()
    must_mention: tuple[str, ...] = ()

    # --- trap ---
    expected_reason: str = ""
    forbidden: tuple[str, ...] = ()
    injection: bool = False

    # --- qualification ---
    expected_tool: str = ""
    expected_arguments: Mapping[str, str] = field(default_factory=dict)
    expected_signals_present: tuple[str, ...] = ()
    expected_score: int = 0
    # The complete `capture_lead` arguments the deterministic subset scripts the stub provider
    # with. `expected_arguments` is its Contact Detail half — the half a real model is expected
    # to reproduce verbatim — and the Qualification Signal phrases here are what a model would
    # have written in its own words, which is not something an expectation can pin.
    stub_arguments: Mapping[str, str] = field(default_factory=dict)

    @property
    def message(self) -> str:
        """The Visitor message a single-Turn case is about."""
        return self.messages[-1] if self.messages else ""


def parse_case(record: Mapping[str, Any]) -> EvalCase:
    """One JSONL record as an Eval Case, or `MalformedCaseError` naming what is wrong."""
    case_id = str(record.get("id") or "").strip()
    if not case_id:
        raise MalformedCaseError(f"An Eval Case needs an id: {record!r}")
    kind = record.get("kind")
    if kind not in KINDS:
        raise MalformedCaseError(f"{case_id}: kind must be one of {KINDS}, not {kind!r}")
    language = record.get("language")
    if language not in LANGUAGES:
        raise MalformedCaseError(
            f"{case_id}: language must be one of {LANGUAGES}, not {language!r}"
        )

    messages = record.get("messages") or ([record["message"]] if record.get("message") else [])
    if not messages:
        raise MalformedCaseError(f"{case_id}: an Eval Case needs a Visitor message")

    return EvalCase(
        id=case_id,
        kind=kind,
        language=language,
        messages=tuple(str(message) for message in messages),
        validated=bool(record.get("validated", False)),
        deterministic=bool(record.get("deterministic", False)),
        golden_answer=str(record.get("golden_answer", "")),
        expected_sections=_strings(record.get("expected_sections")),
        must_mention=_strings(record.get("must_mention")),
        expected_reason=str(record.get("expected_reason", "")),
        forbidden=_strings(record.get("forbidden")),
        injection=bool(record.get("injection", False)),
        expected_tool=str(record.get("expected_tool", "")),
        expected_arguments=dict(record.get("expected_arguments") or {}),
        expected_signals_present=_strings(record.get("expected_signals_present")),
        expected_score=int(record.get("expected_score", 0)),
        stub_arguments=dict(record.get("stub_arguments") or {}),
    )


def load_cases(path: Path = CASES_FILE) -> tuple[EvalCase, ...]:
    """Every Eval Case in the file, in file order. Blank lines and `#` comments are skipped."""
    return tuple(parse_case(record) for record in _records(path))


def deterministic_cases(cases: Sequence[EvalCase]) -> tuple[EvalCase, ...]:
    """The subset CI runs: the cases whose expectations need no model to check."""
    return tuple(case for case in cases if case.deterministic)


def _records(path: Path) -> Iterator[Mapping[str, Any]]:
    with path.open(encoding="utf-8") as lines:
        for number, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as broken:
                raise MalformedCaseError(f"{path}:{number} is not JSON: {broken}") from broken
            if not isinstance(record, dict):
                raise MalformedCaseError(f"{path}:{number} is not a JSON object")
            yield record


def _strings(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(item) for item in value)  # type: ignore[union-attr]
