"""The `Tracer` seam recorded in memory — the whole of Langfuse with no network.

The counterpart of the scriptable `StubModelProvider`: a Trace is not something a test can
read back out of a vendor, so the seam records what it was given and the HTTP tests assert on
that. Nothing here talks to Langfuse, which is why every test and CI run can have tracing on.
"""

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import uuid4

from core.provider import Usage
from core.tracing import TRACE_NAME, ProviderSpan, ToolSpan, TurnTrace

SpanKind = Literal["provider", "tool"]


@dataclass
class RecordedSpan:
    """One provider call or one tool execution, and what it reported."""

    kind: SpanKind
    # The model id for a provider call, the tool's name for a tool execution.
    name: str
    iteration: int = 0
    usage: Usage | None = None
    output_text: str = ""
    produced_events: bool | None = None
    # How the span's block ended: the name of the exception that was travelling through it,
    # or `None` where it simply finished.
    closed_with: str | None = None

    def record_usage(self, usage: Usage, output_text: str) -> None:
        self.usage = usage
        self.output_text = output_text

    def record_events(self, produced_events: bool) -> None:
        self.produced_events = produced_events


@contextmanager
def _recording_how_it_ends(span: RecordedSpan) -> Iterator[None]:
    try:
        yield
    except BaseException as failure:
        span.closed_with = type(failure).__name__
        raise


@dataclass
class RecordedTrace:
    """One Turn's Trace: what it was opened with, what happened inside it, how it ended."""

    trace_id: str
    session_id: str
    request_id: str
    input_text: str
    name: str = TRACE_NAME
    spans: list[RecordedSpan] = field(default_factory=list)
    output_text: str = ""
    usage: Usage = field(default_factory=Usage)
    tags: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    finished: bool = False

    @contextmanager
    def provider_span(self, model: str, iteration: int) -> Iterator[ProviderSpan]:
        span = RecordedSpan(kind="provider", name=model, iteration=iteration)
        self.spans.append(span)
        with _recording_how_it_ends(span):
            yield span

    @contextmanager
    def tool_span(self, name: str) -> Iterator[ToolSpan]:
        span = RecordedSpan(kind="tool", name=name)
        self.spans.append(span)
        with _recording_how_it_ends(span):
            yield span

    def finish(
        self,
        output_text: str,
        usage: Usage,
        tags: Sequence[str],
        metadata: Mapping[str, Any],
    ) -> None:
        self.output_text = output_text
        self.usage = usage
        self.tags = tuple(tags)
        self.metadata = dict(metadata)
        self.finished = True


@dataclass
class RecordingTracer:
    """Every Trace this process opened, in order."""

    traces: list[RecordedTrace] = field(default_factory=list)
    # How many times the process said it was going away. One, at the end, is right.
    shutdowns: int = 0

    def start_turn(self, session_id: str, request_id: str, input_text: str) -> TurnTrace:
        # A thirty-two character hex id, the shape Langfuse gives a Trace, so a test that
        # forgets a Trace id is a string fails here rather than on the deployed service.
        trace = RecordedTrace(
            trace_id=uuid4().hex,
            session_id=session_id,
            request_id=request_id,
            input_text=input_text,
        )
        self.traces.append(trace)
        return trace

    def shutdown(self) -> None:
        self.shutdowns += 1
