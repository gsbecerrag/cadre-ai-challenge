"""The `Tracer` seam against Langfuse Cloud — the only module that knows Langfuse exists.

One Turn is one Trace: a root span named `turn` on the Session the cookie carries, a generation
per provider call with that call's own tokens and the cost OpenRouter reported, and a tool span
per tool the Assistant ran. Latency is the spans' own, so nothing here times anything.

Two things about the way this is written are worth the reader's time.

**Nothing is flushed here.** The SDK batches spans and exports them from its own thread; the
Turn closes the root span after the `done` event has already been streamed and returns. A
Visitor's last frame never waits behind an observability vendor, and a Langfuse outage shows up
as a missing Trace rather than a missing answer (the boundary in `core.tracing` swallows it).

**Trace-level attributes are set on the root span directly.** In the v4 SDK a Trace is the root
span, and its session id, name and tags are OpenTelemetry attributes on it — that is exactly
what `langfuse.propagate_attributes` does under the covers. It cannot be used here because it
is a context manager that has to wrap the creation of the span, and a Turn's tags are only
known when the Turn ends: whether it escalated, captured a Lead, or failed at the provider. So
the same public attribute keys are written straight onto the span, once, at the end.
"""

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from langfuse import Langfuse, LangfuseOtelSpanAttributes, LangfuseSpan

from core.logging import get_logger
from core.provider import Usage
from core.tracing import TRACE_NAME, ProviderSpan, ToolSpan, TurnTrace

logger = get_logger("tracing.langfuse")

# What one model call is called inside a Turn's Trace. The model id is on the generation
# itself, so the name stays the same whichever model answered and the Traces of two models
# line up next to each other.
MODEL_CALL_NAME = "model call"


def _usage_details(usage: Usage) -> dict[str, int]:
    """Langfuse's usage shape. `total` is given rather than left to be summed: the cached
    tokens are part of the input tokens OpenRouter reported, not tokens on top of them, and a
    total that added them would overstate every Turn."""
    return {
        "input": usage.input_tokens,
        "output": usage.output_tokens,
        "cache_read_input_tokens": usage.cached_tokens,
        "total": usage.input_tokens + usage.output_tokens,
    }


def _set_trace_attributes(
    span: LangfuseSpan,
    session_id: str | None = None,
    tags: Sequence[str] | None = None,
    metadata: Mapping[str, str] | None = None,
) -> None:
    """Write the Trace's own attributes onto its root span, using the SDK's public keys."""
    # The one private attribute this adapter touches; the keys it writes are public.
    otel_span = span._otel_span
    if not otel_span.is_recording():
        return
    otel_span.set_attribute(LangfuseOtelSpanAttributes.TRACE_NAME, TRACE_NAME)
    if session_id:
        otel_span.set_attribute(LangfuseOtelSpanAttributes.TRACE_SESSION_ID, session_id)
    if tags:
        otel_span.set_attribute(LangfuseOtelSpanAttributes.TRACE_TAGS, list(tags))
    for key, value in (metadata or {}).items():
        otel_span.set_attribute(f"{LangfuseOtelSpanAttributes.TRACE_METADATA}.{key}", value)


@dataclass(frozen=True)
class LangfuseProviderSpan:
    """One model call. Its usage is the call's own, so a Turn's cost breaks down by call."""

    generation: Any

    def record_usage(self, usage: Usage, output_text: str) -> None:
        self.generation.update(
            output=output_text,
            usage_details=_usage_details(usage),
            # The cost OpenRouter reported for this call, never a price table (ADR-0002).
            cost_details={"total": usage.cost_usd},
        )


@dataclass(frozen=True)
class LangfuseToolSpan:
    """One tool execution. A tool that produced no events either rejected the model's
    arguments or had nothing to show the Visitor, and both are worth seeing."""

    observation: Any

    def record_events(self, produced_events: bool) -> None:
        self.observation.update(metadata={"produced_events": produced_events})


@dataclass(frozen=True)
class LangfuseTurnTrace:
    """One Turn, open from the Visitor's message to after the `done` event."""

    root: LangfuseSpan
    input_text: str

    @property
    def trace_id(self) -> str | None:
        trace_id: str = self.root.trace_id
        return trace_id

    @contextmanager
    def provider_span(self, model: str, iteration: int) -> Iterator[ProviderSpan]:
        generation = self.root.start_observation(
            name=MODEL_CALL_NAME,
            as_type="generation",
            model=model,
            metadata={"iteration": iteration},
        )
        try:
            yield LangfuseProviderSpan(generation)
        finally:
            generation.end()

    @contextmanager
    def tool_span(self, name: str) -> Iterator[ToolSpan]:
        observation = self.root.start_observation(name=name, as_type="tool")
        try:
            yield LangfuseToolSpan(observation)
        finally:
            observation.end()

    def finish(
        self,
        output_text: str,
        usage: Usage,
        tags: Sequence[str],
        metadata: Mapping[str, Any],
    ) -> None:
        # The Turn's totals go on the root span as metadata, not as usage: Langfuse adds a
        # Trace's cost up from its generations, and a root span that also reported the total
        # would charge every Turn twice.
        self.root.update(
            output=output_text,
            metadata={
                **metadata,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cached_tokens": usage.cached_tokens,
                "cost_usd": usage.cost_usd,
            },
        )
        _set_trace_attributes(self.root, tags=tags)
        # Trace-level input and output as well as the root span's own, because that is what
        # the Traces table and the Langfuse evaluators read.
        self.root.set_trace_io(input=self.input_text, output=output_text)
        self.root.end()


class LangfuseTracer:
    """Opens a Trace per Turn against a Langfuse project."""

    def __init__(
        self,
        public_key: str,
        secret_key: str,
        host: str,
        release: str = "",
        environment: str = "development",
    ) -> None:
        self._client = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
            release=release or None,
            environment=environment,
        )
        logger.info("Tracing Turns to Langfuse", extra={"langfuse_host": host})

    def start_turn(self, session_id: str, request_id: str, input_text: str) -> TurnTrace:
        root = self._client.start_observation(
            name=TRACE_NAME,
            as_type="span",
            input=input_text,
        )
        _set_trace_attributes(
            root,
            session_id=session_id,
            # The id a Turn's log lines carry, so Cloud Logging and Langfuse join on it.
            metadata={"request_id": request_id} if request_id else None,
        )
        return LangfuseTurnTrace(root=root, input_text=input_text)
