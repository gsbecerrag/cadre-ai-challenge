"""Run the Eval Cases through the Assistant and print a scorecard.

Two runs, one code path:

- `make eval` builds the application with the real `ModelProvider` and a Haiku judge, runs all
  fifty cases at a concurrency of four, prints the scorecard and writes a JSON report.
- `make eval-stub` (and CI) runs the deterministic subset with the stub `ModelProvider` scripted
  from each case, so a pull request catches a regression in the escalate copy table, the
  Qualification Score or the event contract for nothing.

The application is built by `create_app`, exactly as the container builds it, and driven over
its own HTTP surface through an ASGI transport: the Turn result a metric sees is the parsed
event list a browser would have received, not an internal object this file arranged. The store
is always in memory — an eval run has no business writing to the Session collection a real
Visitor shares — and each case gets its own client, so each case is its own Session.

Nothing here decides what a good answer is. That is `evals/metrics.py`, and the two metrics that
need a model ask `evals/judge.py`.
"""

import argparse
import asyncio
import json
import os
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx2
from fastapi import FastAPI

from api.session import SESSION_COOKIE, session_id_from_cookie
from core.adapters.knowledge_files import FileKnowledgeSource
from core.adapters.memory_store import InMemoryConversationStore
from core.adapters.openrouter_provider import OpenRouterModelProvider
from core.adapters.stub_provider import StubModelProvider, StubResponse
from core.config import Settings
from core.knowledge import KBSection, compile_knowledge_base
from core.logging import configure_logging, get_logger
from core.provider import ModelProvider, TextDelta, ToolCall, Usage
from core.store import Lead
from evals.cases import CASES_FILE, EvalCase, deterministic_cases, load_cases
from evals.judge import Judge, ModelJudge
from evals.metrics import (
    CORRECTNESS,
    ESCALATION_CORRECTNESS,
    GROUNDEDNESS,
    METRIC_NAMES,
    TOOL_CORRECTNESS,
    MetricOutcome,
    TurnResult,
    correctness,
    escalation_correctness,
    groundedness,
    tool_correctness,
)
from evals.sink import EvalSink, build_sink

logger = get_logger("evals.runner")

CAPTURE_LEAD = "capture_lead"
ESCALATE = "escalate"

REPORTS_DIRECTORY = Path(__file__).resolve().parent / "reports"
# A path that is never a built web app: an eval run drives the API, and mounting a stale
# `web/dist` would only change which 404 a typo produces.
NO_WEB_DIST = Path(__file__).resolve().parent / "no-web-app"

# Obviously fake: the Session cookie's signing key for an eval run. Sessions live for the
# length of the process and are never anyone's.
EVAL_COOKIE_SECRET = "eval-session-cookie-secret-not-a-real-one"
EVAL_BASE_URL = "http://evals.invalid"

# Two at a time, not four: a Trap Question is two provider calls (the tool round-trip) and
# a judged case adds one or two more on the judge's own model, so four in flight is well
# past the twenty requests a minute a new OpenRouter account gets. `--concurrency` raises it
# on an account with a real tier.
DEFAULT_CONCURRENCY = 2
DEFAULT_JUDGE_MODEL = "anthropic/claude-haiku-4.5"
# How many times a case is run before its failure is believed, and how long the first wait
# is (it grows by that much each attempt). OpenRouter limits a new account to twenty
# requests a minute per model, and a run of fifty cases will reach it.
DEFAULT_ATTEMPTS = 3
RETRY_PAUSE_SECONDS = 20.0
# The floor on how often a case may start, which is what actually holds the run under a
# per-minute limit: concurrency alone does not, because a fast case frees its slot at once.
DEFAULT_PACE_SECONDS = 3.0

# What the stub provider puts in an Escalation's `next_step`. It is a published route
# (`contact#how-to-reach-cadre`) because `escalate` refuses a call with no next step at all,
# and a scripted next step that named an invented URL would be the very thing the metric is
# looking for.
STUB_NEXT_STEP: Mapping[str, str] = {
    "en": "Use the contact form at https://www.cadreai.com/contact.",
    "es": "Usa el formulario de contacto en https://www.cadreai.com/contact.",
}
# What the stub provider answers a Visitor message that is not the one carrying the tool call.
STUB_ACKNOWLEDGEMENT: Mapping[str, str] = {
    "en": "Thanks — noted. What else can I help with?",
    "es": "Gracias, tomo nota. ¿En qué más te ayudo?",
}

NO_KEY = (
    "OPENROUTER_API_KEY is not set, so the full evaluation run is skipped. Put it in .env "
    "(see .env.example) and run `make eval` again, or run `make eval-stub` for the "
    "deterministic subset, which needs no key."
)


@dataclass(frozen=True)
class CaseScore:
    """Every metric's ruling on one Eval Case, and what the Turn cost."""

    case_id: str
    kind: str
    language: str
    outcomes: tuple[MetricOutcome, ...]
    answer: str = ""
    citations: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()
    cost_usd: float = 0.0
    error: str = ""

    @property
    def errored(self) -> bool:
        """The Turn never produced an answer, so there is nothing here to grade."""
        return bool(self.error)

    @property
    def passed(self) -> bool:
        # An errored case has no outcomes, and `all(())` is True — so this has to say no
        # explicitly, or a run in which every Turn failed would report a clean sweep.
        return not self.errored and all(outcome.passed for outcome in self.outcomes)

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.case_id,
            "kind": self.kind,
            "language": self.language,
            "passed": self.passed,
            "errored": self.errored,
            "metrics": {
                outcome.name: {"passed": outcome.passed, "reason": outcome.reason}
                for outcome in self.outcomes
            },
            "answer": self.answer,
            "citations": list(self.citations),
            "tools": list(self.tools),
            "cost_usd": round(self.cost_usd, 6),
            "error": self.error,
        }


@dataclass(frozen=True)
class Scorecard:
    """One run of the suite: every case's score, and what the whole thing cost."""

    cases: tuple[CaseScore, ...]
    model: str
    judge: str
    started_at: str
    finished_at: str
    judge_cost_usd: float = 0.0
    metric_names: tuple[str, ...] = field(default=METRIC_NAMES)

    @property
    def answer_cost_usd(self) -> float:
        return sum(score.cost_usd for score in self.cases)

    @property
    def cost_usd(self) -> float:
        return self.answer_cost_usd + self.judge_cost_usd

    def rate(self, metric: str) -> tuple[int, int]:
        """How many cases this metric ruled on, and how many of them passed."""
        ruled = [score for score in self.cases if any(o.name == metric for o in score.outcomes)]
        passed = [
            score for score in ruled if all(o.passed for o in score.outcomes if o.name == metric)
        ]
        return len(passed), len(ruled)

    def failing(self, metric: str) -> tuple[tuple[str, str], ...]:
        """The case ids this metric failed, each with the one sentence that says why."""
        return tuple(
            (score.case_id, outcome.reason)
            for score in self.cases
            for outcome in score.outcomes
            if outcome.name == metric and not outcome.passed
        )

    @property
    def errored(self) -> tuple[tuple[str, str], ...]:
        """The cases whose Turn never answered, each with the failure that ended it. They are
        not failures of the Assistant and no metric ruled on them."""
        return tuple((score.case_id, score.error) for score in self.cases if score.errored)

    def as_record(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "judge": self.judge,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "cost_usd": round(self.cost_usd, 6),
            "answer_cost_usd": round(self.answer_cost_usd, 6),
            "judge_cost_usd": round(self.judge_cost_usd, 6),
            "metrics": {
                metric: {
                    "passed": self.rate(metric)[0],
                    "ruled": self.rate(metric)[1],
                    "failing": [case_id for case_id, _reason in self.failing(metric)],
                }
                for metric in self.metric_names
            },
            "errored": [case_id for case_id, _reason in self.errored],
            "cases": [score.as_record() for score in self.cases],
        }


@dataclass(frozen=True)
class Harness:
    """The Assistant, wired in this process: the application and the store behind it."""

    app: FastAPI
    store: InMemoryConversationStore
    provider: ModelProvider


# --- building the Assistant --------------------------------------------------------------


def eval_settings(model_provider: str) -> Settings:
    """The container's settings, with what an eval run must not inherit overridden: the store is
    in memory (a run has no business in the Session collection a real Visitor shares), the
    Session cookie is signed with a throwaway key, and the level is `WARNING` so a scorecard
    is not buried in fifty Turns' worth of structured log lines."""
    return Settings().model_copy(
        update={
            "model_provider": model_provider,
            "conversation_store": "memory",
            "session_cookie_secret": EVAL_COOKIE_SECRET,
            "env": "development",
            "loglevel": "WARNING",
        }
    )


def build_harness(provider: ModelProvider, settings: Settings | None = None) -> Harness:
    # `api.main` builds a module-level `app` on import, because that is what uvicorn loads. It
    # is discarded here, but it reads the environment on the way past, so the eval run's own
    # throwaway cookie key goes in first — otherwise every run opens with a warning about a
    # missing secret that is not missing for the application this file actually builds.
    os.environ.setdefault("SESSION_COOKIE_SECRET", EVAL_COOKIE_SECRET)
    # Imported here rather than at module scope: `api.main` is the composition root and pulls
    # in the whole application, which the case file and the metrics have no need of.
    from api.main import create_app

    store = InMemoryConversationStore()
    resolved = settings or eval_settings("stub")
    app = create_app(settings=resolved, web_dist=NO_WEB_DIST, provider=provider, store=store)
    return Harness(app=app, store=store, provider=provider)


def stub_script(
    case: EvalCase,
) -> tuple[Mapping[str, Sequence[StubResponse]], Sequence[StubResponse]]:
    """The scripts and the fallback that turn one Eval Case into a scripted stub provider.

    The scripted response *is* the case's expectation — an `escalate` call with its reason, or a
    `capture_lead` call with its arguments — so what runs afterwards is the plumbing: the copy
    table, the merge, the score, the events. The second response in each script carries no tool
    call, which is how the Turn loop is told the model is done.
    """
    trigger = case.messages[-1]
    if case.kind == "trap":
        call = ToolCall(
            id=f"eval-{case.id}",
            name=ESCALATE,
            arguments={
                "reason": case.expected_reason,
                "known": "",
                "next_step": STUB_NEXT_STEP[case.language],
                "language": case.language,
            },
        )
    elif case.kind == "qualification":
        call = ToolCall(
            id=f"eval-{case.id}", name=CAPTURE_LEAD, arguments=dict(case.stub_arguments)
        )
    else:
        raise ValueError(
            f"{case.id}: only a deterministic Eval Case can be scripted; whether the Assistant "
            "answers an in-KB question correctly is what `make eval` asks."
        )
    acknowledgement = STUB_ACKNOWLEDGEMENT[case.language]
    scripts = {trigger: ((call,), (TextDelta(acknowledgement), Usage()))}
    return scripts, ((TextDelta(acknowledgement), Usage()),)


def stub_harness(case: EvalCase) -> Harness:
    scripts, fallback = stub_script(case)
    return build_harness(StubModelProvider(scripts=scripts, fallback=fallback))


def openrouter_harness(settings: Settings) -> Harness:
    return build_harness(
        OpenRouterModelProvider(
            api_key=settings.openrouter_api_key,
            model=settings.chat_model,
            app_url=settings.openrouter_app_url,
            app_name=settings.openrouter_app_name,
            cache_ttl=settings.prompt_cache_ttl,
            base_url=settings.openrouter_base_url,
        ),
        settings,
    )


def build_judge(settings: Settings, model: str) -> ModelJudge:
    """The judge: the same adapter, a second instance, a cheaper model (ADR-0008)."""
    return ModelJudge(
        OpenRouterModelProvider(
            api_key=settings.openrouter_api_key,
            model=model,
            app_url=settings.openrouter_app_url,
            app_name=settings.openrouter_app_name,
            cache_ttl=settings.prompt_cache_ttl,
            base_url=settings.openrouter_base_url,
        ),
        model=model,
    )


# --- running a case ----------------------------------------------------------------------


def parse_sse(body: str) -> list[tuple[str, Mapping[str, Any]]]:
    """The `(name, payload)` pairs a browser's parser would see. The same shape the HTTP tests
    read, so the metrics grade what a Visitor was actually sent."""
    events: list[tuple[str, Mapping[str, Any]]] = []
    for frame in body.split("\n\n"):
        if not frame.strip():
            continue
        name_line, _, data_line = frame.partition("\n")
        events.append(
            (
                name_line.removeprefix("event: "),
                json.loads(data_line.removeprefix("data: ")),
            )
        )
    return events


async def run_case(case: EvalCase, harness: Harness) -> TurnResult:
    """One Eval Case as one Session: every message in order, then the Lead it left behind."""
    transport = httpx2.ASGITransport(app=harness.app)
    events: list[tuple[str, Mapping[str, Any]]] = []
    cost = 0.0
    error = ""
    lead: Lead | None = None
    async with httpx2.AsyncClient(
        transport=transport, base_url=EVAL_BASE_URL, timeout=180.0
    ) as client:
        for message in case.messages:
            response = await client.post("/api/chat", json={"message": message})
            if response.status_code != 200:
                error = f"HTTP {response.status_code} from /api/chat"
                break
            for name, payload in parse_sse(response.text):
                events.append((name, payload))
                if name == "done":
                    cost += float((payload.get("usage") or {}).get("cost_usd") or 0.0)
                elif name == "error":
                    error = str(payload.get("message", ""))
        session_id = session_id_from_cookie(
            client.cookies.get(SESSION_COOKIE) or "", EVAL_COOKIE_SECRET
        )
    if session_id:
        lead = await harness.store.get_lead(session_id)
    return TurnResult(
        events=tuple(events), lead=lead, turns=len(case.messages), cost_usd=cost, error=error
    )


class Pacer:
    """A floor on how often a case may start. Not a token bucket: the run is fifty cases long
    and the only thing that has to hold is the average, so one lock and a clock is enough."""

    def __init__(self, seconds: float) -> None:
        self._seconds = max(0.0, seconds)
        self._lock = asyncio.Lock()
        self._last = 0.0

    async def wait(self) -> None:
        if not self._seconds:
            return
        async with self._lock:
            now = asyncio.get_running_loop().time()
            due = self._last + self._seconds
            if now < due:
                await asyncio.sleep(due - now)
            self._last = asyncio.get_running_loop().time()


async def run_case_until_answered(
    case: EvalCase, harness: Harness, attempts: int = DEFAULT_ATTEMPTS
) -> TurnResult:
    """The case, retried from a fresh Session while the Turn ends in a provider failure.

    A Turn that ends in an `error` event produced no answer at all, so grading it measures the
    provider's rate limiter rather than the Assistant — and on a new OpenRouter account that
    limiter is twenty requests a minute per model, which fifty cases will reach. The Turn loop
    deliberately does not retry (a Visitor gets one honest failure, ADR-0004), so the retry
    belongs here, in the harness that can afford to wait, and nowhere near the request path.
    """
    result = await run_case(case, harness)
    for attempt in range(1, attempts):
        if not result.error:
            return result
        pause = RETRY_PAUSE_SECONDS * attempt
        logger.warning(
            "Retrying an Eval Case after a provider failure",
            extra={"eval_case": case.id, "attempt": attempt, "pause_seconds": pause},
        )
        await asyncio.sleep(pause)
        result = await run_case(case, harness)
    return result


def run_case_against_stub(case: EvalCase) -> TurnResult:
    """One deterministic Eval Case, driven through a freshly wired Assistant with the stub
    provider scripted from the case. Synchronous, because pytest is."""
    return asyncio.run(run_case(case, stub_harness(case)))


async def score_case(
    case: EvalCase,
    result: TurnResult,
    judge: Judge | None,
    sections: Mapping[str, KBSection],
) -> CaseScore:
    """Every metric that applies to this kind of case, in scorecard order.

    Groundedness applies to all three kinds — it is a property of an answer, not of an
    expectation — and is skipped only when there is no judge, which is the stub run.

    A Turn that ended in an `error` event is not graded at all. It has already been retried
    from a fresh Session as many times as `--attempts` allows, so what is left is the provider
    saying no, and grading that measures the provider: the Assistant would fail
    `escalation_correctness` for an Escalation it never got to raise, and pass `groundedness`
    for an answer it never got to write. The case is recorded as errored, counted by no metric,
    and printed apart from the failures — a run with errors in it is a run to repeat, not a
    verdict to read.
    """
    if result.error:
        return CaseScore(
            case_id=case.id,
            kind=case.kind,
            language=case.language,
            outcomes=(),
            answer=result.answer,
            citations=result.citations,
            tools=result.tool_names,
            cost_usd=result.cost_usd,
            error=result.error,
        )
    outcomes: list[MetricOutcome] = []
    if case.kind == "in_kb" and judge is not None:
        outcomes.append(await correctness(case, result, judge))
    if case.kind == "trap":
        outcomes.append(escalation_correctness(case, result))
    if case.kind == "qualification":
        outcomes.append(tool_correctness(case, result))
    if judge is not None:
        outcomes.append(await groundedness(case, result, judge, sections))
    return CaseScore(
        case_id=case.id,
        kind=case.kind,
        language=case.language,
        outcomes=tuple(outcomes),
        answer=result.answer,
        citations=result.citations,
        tools=result.tool_names,
        cost_usd=result.cost_usd,
        error=result.error,
    )


async def run_suite(
    cases: Sequence[EvalCase],
    harness: Harness,
    judge: Judge | None,
    sections: Mapping[str, KBSection],
    *,
    model: str,
    judge_model: str,
    concurrency: int = DEFAULT_CONCURRENCY,
    attempts: int = DEFAULT_ATTEMPTS,
    pace_seconds: float = DEFAULT_PACE_SECONDS,
) -> Scorecard:
    """Every case, at most `concurrency` in flight. One Session each, one score each."""
    started = _now()
    gate = asyncio.Semaphore(concurrency)
    pacer = Pacer(pace_seconds)

    async def one(case: EvalCase) -> CaseScore:
        async with gate:
            await pacer.wait()
            try:
                result = await run_case_until_answered(case, harness, attempts)
            # Broad on purpose: one Eval Case that crashes is one failing row in the
            # scorecard, not a run of forty-nine other cases thrown away.
            except Exception as failed:
                logger.exception("Eval Case crashed", extra={"eval_case": case.id})
                result = TurnResult(error=f"{type(failed).__name__}: {failed}")
            return await score_case(case, result, judge, sections)

    scores = await asyncio.gather(*(one(case) for case in cases))
    judge_cost = judge.usage.cost_usd if isinstance(judge, ModelJudge) else 0.0
    return Scorecard(
        cases=tuple(scores),
        model=model,
        judge=judge_model,
        started_at=started,
        finished_at=_now(),
        judge_cost_usd=judge_cost,
    )


# --- reporting ---------------------------------------------------------------------------


def render_scorecard(scorecard: Scorecard) -> str:
    """The scorecard a Cadre engineer reads: a rate per metric, then every failing case."""
    lines = [
        "",
        f"Eval scorecard — {len(scorecard.cases)} Eval Cases",
        f"  model {scorecard.model}   judge {scorecard.judge}",
        "",
    ]
    for metric in scorecard.metric_names:
        passed, ruled = scorecard.rate(metric)
        if not ruled:
            continue
        percent = 100.0 * passed / ruled
        lines.append(f"  {metric:<24} {passed:>3}/{ruled:<3} {percent:5.1f}%")
    lines.append("")
    failures = [
        (metric, case_id, reason)
        for metric in scorecard.metric_names
        for case_id, reason in scorecard.failing(metric)
    ]
    if failures:
        lines.append(f"  Failing Eval Cases ({len(failures)}):")
        lines.extend(f"    {case_id} [{metric}] {reason}" for metric, case_id, reason in failures)
    else:
        lines.append("  Every Eval Case passed every metric that ruled on it.")
    if scorecard.errored:
        # Kept apart from the failures on purpose: these are cases no metric ruled on, and
        # reading them as failures of the Assistant is exactly the mistake to avoid.
        lines.append("")
        lines.append(f"  Errored Eval Cases ({len(scorecard.errored)}) — not graded:")
        lines.extend(f"    {case_id} {reason}" for case_id, reason in scorecard.errored)
    lines.extend(
        [
            "",
            f"  cost  answers ${scorecard.answer_cost_usd:.4f}  "
            f"judge ${scorecard.judge_cost_usd:.4f}  total ${scorecard.cost_usd:.4f}",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(scorecard: Scorecard, directory: Path = REPORTS_DIRECTORY) -> Path:
    """The run as JSON, for the benchmark ticket to read back per model (ADR-0008)."""
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    path = directory / f"{stamp}-{scorecard.model.replace('/', '-')}.json"
    path.write_text(json.dumps(scorecard.as_record(), indent=2, ensure_ascii=False), "utf-8")
    return path


def emit(text: str) -> None:
    """The scorecard goes to stdout as a report for a human, not through the structured logger:
    a table is not a log line, and `print` is a lint error in this repository."""
    sys.stdout.write(text + "\n")
    sys.stdout.flush()


def _now() -> str:
    return datetime.now(tz=UTC).isoformat(timespec="seconds")


# --- the command ---------------------------------------------------------------------------


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m evals.runner",
        description="Run the Eval Cases through the Assistant and print a scorecard.",
    )
    parser.add_argument("--cases", type=Path, default=CASES_FILE, help="the JSONL case file")
    parser.add_argument(
        "--stub",
        action="store_true",
        help="run the deterministic subset against the stub provider; no key, no spend",
    )
    parser.add_argument("--kind", choices=("in_kb", "trap", "qualification"), help="one kind only")
    parser.add_argument("--limit", type=int, default=0, help="run only the first N cases")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument(
        "--attempts",
        type=int,
        default=DEFAULT_ATTEMPTS,
        help="how many times a case is run before a provider failure is believed",
    )
    parser.add_argument(
        "--pace",
        type=float,
        default=DEFAULT_PACE_SECONDS,
        help="minimum seconds between the start of one case and the next",
    )
    parser.add_argument("--reports", type=Path, default=REPORTS_DIRECTORY)
    parser.add_argument("--no-report", action="store_true", help="print, do not write JSON")
    return parser.parse_args(argv)


def select(cases: Sequence[EvalCase], arguments: argparse.Namespace) -> tuple[EvalCase, ...]:
    chosen = deterministic_cases(cases) if arguments.stub else tuple(cases)
    if arguments.kind:
        chosen = tuple(case for case in chosen if case.kind == arguments.kind)
    if arguments.limit:
        chosen = chosen[: arguments.limit]
    return chosen


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parse_arguments(argv)
    configure_logging(level="WARNING")
    cases = select(load_cases(arguments.cases), arguments)
    sections = {
        section.id: section for section in compile_knowledge_base(FileKnowledgeSource().documents())
    }

    if arguments.stub:
        # One harness per case, because the stub is scripted from the case it is answering.
        scorecard = asyncio.run(_run_stub_suite(cases, arguments.concurrency, sections))
    else:
        settings = eval_settings("openrouter")
        if not settings.openrouter_api_key.strip():
            emit(NO_KEY)
            return 0
        judge_model = os.environ.get("JUDGE_MODEL", "").strip() or DEFAULT_JUDGE_MODEL
        judge = build_judge(settings, judge_model)
        scorecard = asyncio.run(
            run_suite(
                cases,
                openrouter_harness(settings),
                judge,
                sections,
                model=settings.chat_model,
                judge_model=judge_model,
                concurrency=arguments.concurrency,
                attempts=arguments.attempts,
                pace_seconds=arguments.pace,
            )
        )

    emit(render_scorecard(scorecard))
    if not arguments.no_report:
        emit(f"  report {write_report(scorecard, arguments.reports)}")
    build_sink().publish(scorecard)
    failed = [score.case_id for score in scorecard.cases if not score.passed]
    return 1 if failed else 0


async def _run_stub_suite(
    cases: Sequence[EvalCase], concurrency: int, sections: Mapping[str, KBSection]
) -> Scorecard:
    started = _now()
    gate = asyncio.Semaphore(concurrency)

    async def one(case: EvalCase) -> CaseScore:
        async with gate:
            result = await run_case(case, stub_harness(case))
            return await score_case(case, result, None, sections)

    scores = await asyncio.gather(*(one(case) for case in cases))
    return Scorecard(
        cases=tuple(scores),
        model="stub",
        judge="none",
        started_at=started,
        finished_at=_now(),
        metric_names=(ESCALATION_CORRECTNESS, TOOL_CORRECTNESS),
    )


__all__ = [
    "CAPTURE_LEAD",
    "CORRECTNESS",
    "ESCALATE",
    "GROUNDEDNESS",
    "CaseScore",
    "EvalSink",
    "Harness",
    "Scorecard",
    "main",
    "run_case",
    "run_case_against_stub",
    "run_suite",
]

if __name__ == "__main__":
    raise SystemExit(main())
