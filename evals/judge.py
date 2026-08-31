"""The judge: a cheaper model, behind the same `ModelProvider` seam as the Assistant.

Two of the four metrics cannot be decided by a string comparison — whether an answer says the
same thing as the golden answer, and whether every claim in it is carried by the KB Sections it
cited. Both tolerate paraphrase, so both go to a model. It is Haiku 4.5 rather than the
Assistant's Sonnet 5 because grading a paragraph against a paragraph is the cheap tier of work
Cadre itself publishes for that tier (`partners-and-models#matching-the-model-to-the-task`), and
because a judge costs one call per metric per case (ADR-0008).

It runs through `ModelProvider` — the same adapter, a second instance with the judge's model —
so the judge has no HTTP client, no key handling and no retry policy of its own, and the S2
tests stub it out with a two-line class.

A judge is asked for one JSON object and nothing else. Models answer that with a code fence, a
preamble, or an apology often enough that parsing has to be defensive: an unparseable verdict
fails the case and says what came back, because a judge that cannot be read is not evidence
that an answer was good.
"""

import asyncio
import json
import re
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from core.knowledge import KBSection
from core.logging import get_logger
from core.prompt import SystemPrompt
from core.provider import (
    ModelMessage,
    ModelProvider,
    ProviderError,
    ProviderRequest,
    TextDelta,
    Usage,
)

logger = get_logger("evals.judge")

JUDGE_SYSTEM = """\
You grade one answer written by the Cadre AI Assistant against a rubric. You are not talking to
a Visitor, you are not answering the Visitor's question, and you are not improving the answer.

Reply with one JSON object and nothing else, in exactly this shape:
{"pass": true, "reason": "<one short sentence>"}

No markdown, no code fence, no preamble, no trailing commentary."""

# Kept non-empty on purpose: the prompt is sent as two content parts (a cached one and a
# volatile one) and an empty text part is rejected by some upstreams.
JUDGE_VOLATILE = "Answer with the JSON object only."

CORRECTNESS_INSTRUCTION = """\
Grade CORRECTNESS.

The golden answer is what the Knowledge Base says about the Visitor's question. Pass when the
Assistant's answer carries the facts of the golden answer, in any wording, any order and any
language. Paraphrase, a different structure, a shorter answer, citation markers in square
brackets and a follow-up question to the Visitor are all fine, and none of them is a failure.

Extra facts are NOT a failure. The golden answer is a floor, not a ceiling: the Assistant reads
the whole Knowledge Base and may add related detail the golden answer left out. Whether an extra
fact is actually published is a different question, asked by a different grader.

Fail only when a fact the golden answer carries is missing from the answer, or when the answer
contradicts the golden answer - a different number, a different name, the opposite claim.

Visitor question:
{question}

Golden answer:
{golden_answer}

The Assistant's answer:
{answer}"""

GROUNDEDNESS_INSTRUCTION = """\
Grade GROUNDEDNESS.

Below are the KB Sections the Assistant cited, with their text, and the answer the Visitor
read. Pass when every factual claim in the answer is supported by the text of one of those
sections. Fail when any claim is not — a number, a price, a URL, a date, a person, a
certification, a capability, a promise. Judge support only: never style, length, tone or
whether the answer was complete. A question the Assistant asks the Visitor is not a claim, and
neither is a statement that Cadre does not publish something when a section says so.

Cited KB Sections:
{sections}

The Assistant's answer:
{answer}"""

NO_SECTIONS = "(the answer cited no KB Section)"

# Same shape as the runner's retry on a rate-limited Turn, for the same reason.
DEFAULT_ATTEMPTS = 3
RETRY_PAUSE_SECONDS = 20.0

_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)
_TRUE_WORDS = frozenset({"true", "yes", "pass", "passed", "1"})
_FALSE_WORDS = frozenset({"false", "no", "fail", "failed", "0"})


@dataclass(frozen=True)
class Verdict:
    """What the judge decided, and why in one sentence."""

    passed: bool
    reason: str


class Judge(Protocol):
    """Grades one rubric instruction. The metric writes the instruction; the judge rules."""

    async def rule(self, instruction: str) -> Verdict: ...


def parse_verdict(answer: str) -> Verdict:
    """The judge's JSON, read defensively. Anything unreadable fails the case and says so."""
    match = _JSON_OBJECT.search(answer)
    if match is not None:
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            decided = _decide(parsed)
            if decided is not None:
                return Verdict(passed=decided, reason=_reason_of(parsed))
    logger.warning("The judge returned no verdict", extra={"judge_answer": answer[:200]})
    return Verdict(passed=False, reason=f"the judge returned no verdict: {answer.strip()[:200]}")


def render_sections(sections: Sequence[KBSection]) -> str:
    """The cited sections as the judge reads them: the id it was cited by, then its own text."""
    if not sections:
        return NO_SECTIONS
    return "\n\n".join(f"[{section.id}] {section.heading}\n{section.body}" for section in sections)


def correctness_instruction(question: str, golden_answer: str, answer: str) -> str:
    return CORRECTNESS_INSTRUCTION.format(
        question=question, golden_answer=golden_answer, answer=answer
    )


def groundedness_instruction(sections: Sequence[KBSection], answer: str) -> str:
    return GROUNDEDNESS_INSTRUCTION.format(sections=render_sections(sections), answer=answer)


class ModelJudge:
    """A `Judge` backed by a `ModelProvider`. One provider call per verdict, no history."""

    def __init__(
        self, provider: ModelProvider, *, model: str = "", attempts: int = DEFAULT_ATTEMPTS
    ) -> None:
        self._provider = provider
        self._attempts = max(1, attempts)
        self.model = model
        self.usage = Usage()
        self.calls = 0

    async def rule(self, instruction: str) -> Verdict:
        """One verdict, retried while the provider says the failure is worth retrying.

        A judge that was rate-limited is not evidence about the answer it never read, and on a
        new OpenRouter account seventy judge calls will meet the twenty-a-minute limit.
        """
        for attempt in range(1, self._attempts + 1):
            verdict, retryable = await self._attempt(instruction)
            if not retryable or attempt == self._attempts:
                return verdict
            await asyncio.sleep(RETRY_PAUSE_SECONDS * attempt)
        return verdict

    async def _attempt(self, instruction: str) -> tuple[Verdict, bool]:
        request = ProviderRequest(
            prompt=SystemPrompt(
                cached_sections=(("judge", JUDGE_SYSTEM),), volatile=JUDGE_VOLATILE
            ),
            messages=(ModelMessage(role="visitor", content=instruction),),
        )
        deltas: list[str] = []
        try:
            async for event in self._stream(request):
                if isinstance(event, TextDelta):
                    deltas.append(event.text)
                elif isinstance(event, Usage):
                    self.usage = self.usage + event
        except ProviderError as unreachable:
            # A judge that could not be reached is not a verdict against the Assistant, but it
            # is not a pass either: once the retries are spent the case fails and says the
            # judge is why, rather than passing on an answer nobody graded.
            logger.warning(
                "The judge could not be reached", extra={"provider_error": unreachable.detail}
            )
            return (
                Verdict(
                    passed=False, reason=f"the judge could not be reached: {unreachable.detail}"
                ),
                unreachable.retryable,
            )
        self.calls += 1
        return parse_verdict("".join(deltas)), False

    def _stream(self, request: ProviderRequest) -> AsyncIterator[Any]:
        return self._provider.stream(request)


def _decide(parsed: dict[str, Any]) -> bool | None:
    for key in ("pass", "passed", "result", "verdict"):
        if key not in parsed:
            continue
        value = parsed[key]
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            folded = value.strip().casefold()
            if folded in _TRUE_WORDS:
                return True
            if folded in _FALSE_WORDS:
                return False
    return None


def _reason_of(parsed: dict[str, Any]) -> str:
    for key in ("reason", "explanation", "why"):
        if isinstance(parsed.get(key), str):
            return str(parsed[key]).strip()
    return ""
