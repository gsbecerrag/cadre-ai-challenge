"""The `Tracer` seam: every Turn is a Trace, and this is what a Trace carries.

A Cadre engineer opens Langfuse and reads a conversation as a Session of Traces, one per Turn,
with the model, the tokens and cached tokens, the cost OpenRouter reported, the latency, a span
per provider call and per tool execution, the KB Sections the answer cited, and tags for what
the Turn did. None of that is worth a Visitor's answer, so two rules hold at this boundary and
nowhere else:

- **A Trace body is redacted.** Input and output go through the `full` Redaction Profile on
  their way out — the Refuse Set gone and Contact Details tokenised — because Langfuse Cloud is
  somebody other than the Strategist handling the Lead (ADR-0006). It is done here rather than
  at each call site for the reason `core.logging` does the same: one place, so a field added
  next month cannot be the one that leaks.
- **A tracer cannot break a Turn.** Every call into an implementation is wrapped: a Langfuse
  outage, a rejected span, a broken key logs an exception and the Turn carries on. Whatever
  observability is worth, it is not worth an error event.

`TraceBoundary` is those two rules; `NoopTracer` is the default everywhere but the deployed
service, so tests, CI and `make dev` run the whole Turn with tracing off and no key.
"""

import sys
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from types import TracebackType
from typing import Any, Protocol

from core import redaction
from core.logging import get_logger
from core.provider import Usage

logger = get_logger("tracing")

# What `sys.exc_info()` returns: how a `with` block ended, in the shape `__exit__` takes.
_ExcInfo = tuple[type[BaseException], BaseException, TracebackType] | tuple[None, None, None]

# What one Turn is called in Langfuse. Every Trace has this name, so a Session reads as a
# column of Turns and a filter on the name is a filter on "conversations".
TRACE_NAME = "turn"

# The tag a Turn that ended in a `ProviderError` carries: the Turns worth reading first.
PROVIDER_ERROR_TAG = "provider_error"
# The tag a Turn the Visitor walked out of carries. It is not a failure — an answer that took
# too long, a question already answered, a closed laptop — but it is the one ending that leaves
# nothing in the Session, so the Trace is all there is.
CLIENT_DISCONNECTED_TAG = "client_disconnected"
LANGUAGE_TAG_PREFIX = "language:"
# One tag per redaction category the Turn saw, so "how often do Visitors paste a card" is a
# filter rather than a query over metadata (ADR-0006).
REDACTED_TAG_PREFIX = "redacted:"

# What a tool having run says about the Turn, in the order the tags are written. `escalate`
# means the Assistant refused honestly, `capture_lead` means a Lead landed, `show_walkthrough`
# means the Visitor got a route instead of a paragraph — the three things worth filtering a
# week of conversations by. Ticket 11's `offer_live_handover` slots in without a code change
# anywhere else.
TOOL_TAGS: Mapping[str, str] = {
    "escalate": "escalated",
    "capture_lead": "lead_captured",
    "show_walkthrough": "walkthrough_shown",
    "offer_live_handover": "handover_offered",
}


def turn_tags(
    tools_run: Sequence[str],
    language: str | None = None,
    provider_error: bool = False,
    redactions: Mapping[str, int] | None = None,
    disconnected: bool = False,
) -> tuple[str, ...]:
    """The tags for one Turn, in a fixed order and each one once.

    Pure, because this is the vocabulary a Cadre engineer filters a week of conversations by
    and it should be arguable without running a Turn. A tool that was called but rejected its
    own arguments still tags the Trace: the Assistant tried to escalate, and that a refusal
    failed to render is the more interesting Turn, not the less.
    """
    tags = [tag for name, tag in TOOL_TAGS.items() if name in tools_run]
    if language:
        tags.append(f"{LANGUAGE_TAG_PREFIX}{language}")
    if provider_error:
        tags.append(PROVIDER_ERROR_TAG)
    if disconnected:
        tags.append(CLIENT_DISCONNECTED_TAG)
    tags.extend(f"{REDACTED_TAG_PREFIX}{category}" for category in sorted(redactions or {}))
    return tuple(dict.fromkeys(tags))


class ProviderSpan(Protocol):
    """One model call inside a Turn. Its usage is the call's own, not the Turn's total."""

    def record_usage(self, usage: Usage, output_text: str) -> None: ...


class ToolSpan(Protocol):
    """One tool execution inside a Turn."""

    def record_events(self, produced_events: bool) -> None: ...


class TurnTrace(Protocol):
    """One Turn's Trace, open from the moment the Visitor's message is read."""

    @property
    def trace_id(self) -> str | None:
        """Known before the Turn runs, because the `done` event carries it to the browser and
        ticket 12's Feedback attaches to it. `None` means tracing is off."""

    def provider_span(self, model: str, iteration: int) -> AbstractContextManager[ProviderSpan]: ...

    def tool_span(self, name: str) -> AbstractContextManager[ToolSpan]: ...

    def finish(
        self,
        output_text: str,
        usage: Usage,
        tags: Sequence[str],
        metadata: Mapping[str, Any],
    ) -> None:
        """Close the Trace. Called after the `done` event has been streamed, so nothing an
        observability vendor does is on the Visitor's critical path."""


class Tracer(Protocol):
    """Opens a Trace for a Turn. One production implementation (Langfuse), one null object."""

    def start_turn(self, session_id: str, request_id: str, input_text: str) -> TurnTrace: ...

    def shutdown(self) -> None:
        """Send whatever is still queued, because the process is going away.

        Called once, from the application's shutdown hook. Cloud Run reclaims an instance
        minutes after its last Turn and gives an exporter's background thread almost no CPU in
        between, so a Trace that was only queued is a Trace nobody will ever read.
        """


# ------------------------------------------------------------------ tracing switched off


class NoopSpan:
    """A span that records nothing, so the Turn's instrumentation is unconditional."""

    def record_usage(self, usage: Usage, output_text: str) -> None:
        return

    def record_events(self, produced_events: bool) -> None:
        return


NOOP_SPAN = NoopSpan()


class NoopTurnTrace:
    """A Trace that never existed: no id for the `done` event, nothing recorded."""

    @property
    def trace_id(self) -> str | None:
        return None

    @contextmanager
    def provider_span(self, model: str, iteration: int) -> Iterator[ProviderSpan]:
        yield NOOP_SPAN

    @contextmanager
    def tool_span(self, name: str) -> Iterator[ToolSpan]:
        yield NOOP_SPAN

    def finish(
        self,
        output_text: str,
        usage: Usage,
        tags: Sequence[str],
        metadata: Mapping[str, Any],
    ) -> None:
        return


NOOP_TRACE = NoopTurnTrace()


class NoopTracer:
    """Tracing off — the default without Langfuse keys, which is CI, `make dev` and every
    reviewer's laptop. The Turn is instrumented exactly the same way and nothing leaves."""

    def start_turn(self, session_id: str, request_id: str, input_text: str) -> TurnTrace:
        return NOOP_TRACE

    def shutdown(self) -> None:
        return


# ---------------------------------------------------------------------- the boundary


@dataclass(frozen=True)
class TraceBoundary:
    """Wraps any `Tracer` in the two rules every Trace obeys: bodies through the `full`
    Redaction Profile, and no exception from a tracer reaching the Turn."""

    inner: Tracer

    def start_turn(self, session_id: str, request_id: str, input_text: str) -> TurnTrace:
        try:
            return _GuardedTrace(
                self.inner.start_turn(
                    session_id=session_id,
                    request_id=request_id,
                    input_text=redaction.full(input_text).text,
                )
            )
        except Exception:
            logger.exception("Tracing could not start a Trace")
            return NOOP_TRACE

    def shutdown(self) -> None:
        try:
            self.inner.shutdown()
        except Exception:
            logger.exception("Tracing could not flush what it had queued")


def _close(manager: AbstractContextManager[Any] | None, failure: _ExcInfo) -> None:
    """Leave the wrapped span, telling it how the block ended and swallowing what it says."""
    if manager is None:
        return
    try:
        manager.__exit__(*failure)
    except Exception:
        logger.exception("Tracing could not close a span")


@dataclass(frozen=True)
class _GuardedSpan:
    """A span whose recording cannot raise and whose text is redacted. `inner` is `None` when
    opening the span failed, which is how a Turn keeps running with half a Trace."""

    inner: Any

    def record_usage(self, usage: Usage, output_text: str) -> None:
        if self.inner is None:
            return
        try:
            self.inner.record_usage(usage=usage, output_text=redaction.full(output_text).text)
        except Exception:
            logger.exception("Tracing could not record a provider call")

    def record_events(self, produced_events: bool) -> None:
        if self.inner is None:
            return
        try:
            self.inner.record_events(produced_events=produced_events)
        except Exception:
            logger.exception("Tracing could not record a tool execution")


@dataclass(frozen=True)
class _GuardedTrace:
    inner: TurnTrace

    @property
    def trace_id(self) -> str | None:
        try:
            return self.inner.trace_id
        except Exception:
            logger.exception("Tracing could not name the Trace")
            return None

    def provider_span(self, model: str, iteration: int) -> AbstractContextManager[ProviderSpan]:
        return self._span(lambda: self.inner.provider_span(model=model, iteration=iteration))

    def tool_span(self, name: str) -> AbstractContextManager[ToolSpan]:
        return self._span(lambda: self.inner.tool_span(name=name))

    def finish(
        self,
        output_text: str,
        usage: Usage,
        tags: Sequence[str],
        metadata: Mapping[str, Any],
    ) -> None:
        try:
            self.inner.finish(
                output_text=redaction.full(output_text).text,
                usage=usage,
                tags=tuple(tags),
                metadata=dict(metadata),
            )
        except Exception:
            logger.exception("Tracing could not finish the Trace")

    @contextmanager
    def _span(self, open_span: Callable[[], AbstractContextManager[Any]]) -> Iterator[_GuardedSpan]:
        """Enter the wrapped span, or carry on without one.

        The two `try` blocks are separate on purpose: an exception raised by the Turn inside
        the `with` — a `ProviderError` mid-answer, or the `GeneratorExit` of a Visitor closing
        the tab — must travel on out, and one `try` around the `yield` would swallow it. It is
        also handed to the wrapped span on the way past, so that a model call that died halfway
        is marked as failed in the Trace rather than reading like one that simply ended.
        """
        manager: AbstractContextManager[Any] | None = None
        span: Any = None
        try:
            manager = open_span()
            span = manager.__enter__()
        except Exception:
            logger.exception("Tracing could not open a span")
            manager, span = None, None
        try:
            yield _GuardedSpan(span)
        except BaseException:
            _close(manager, sys.exc_info())
            raise
        else:
            _close(manager, (None, None, None))
