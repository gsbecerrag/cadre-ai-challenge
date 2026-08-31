"""The Langfuse adapter's span lifetime — seam S2, with a stand-in for the SDK's span.

Nothing here talks to Langfuse: the SDK is imported (the adapter is the only module that may)
but no client is built and no span is exported. What is pinned is the one thing the tracing
boundary in `core.tracing` cannot do for the adapter — the boundary keeps a Turn alive when a
tracer raises, but only the adapter can make sure the span it opened is closed on the way out.
An open span is worse than a missing one: it is a Trace that never arrives and a Turn that
looks like it never ended.
"""

from typing import cast

import pytest
from langfuse import LangfuseSpan

from core.adapters.langfuse_tracer import LangfuseTurnTrace, _set_trace_attributes
from core.provider import Usage

SPEND = Usage(input_tokens=12_400, output_tokens=48, cached_tokens=12_200, cost_usd=0.0031)
ANSWER = "Cadre AI is a consultancy focused on revenue growth and EBITDA."


class FakeOtelSpan:
    def __init__(self, recording: bool = True) -> None:
        self.recording = recording
        self.attributes: dict[str, object] = {}

    def is_recording(self) -> bool:
        return self.recording

    def set_attribute(self, key: str, value: object) -> None:
        self.attributes[key] = value


class FakeRoot:
    """What the SDK hands back from `start_observation`, as much of it as the adapter uses."""

    def __init__(self, fails_on: str = "", otel_span: FakeOtelSpan | None = None) -> None:
        self._fails_on = fails_on
        self._otel_span = otel_span if otel_span is not None else FakeOtelSpan()
        self.ended = False
        self.trace_id = "a" * 32

    def _maybe_fail(self, call: str) -> None:
        if call == self._fails_on:
            raise RuntimeError(f"the SDK rejected {call}")

    def update(self, **kwargs: object) -> None:
        self._maybe_fail("update")

    def set_trace_io(self, input: str, output: str) -> None:
        self._maybe_fail("set_trace_io")

    def end(self) -> None:
        self.ended = True


class RootWithoutAnOtelSpan(FakeRoot):
    """A future SDK that has renamed the private attribute the tags are written through."""

    def __init__(self) -> None:
        super().__init__()
        del self._otel_span


def finish(root: FakeRoot, tags: tuple[str, ...] = ("escalated",)) -> None:
    trace = LangfuseTurnTrace(root=cast(LangfuseSpan, root), input_text="What does Cadre do?")
    trace.finish(output_text=ANSWER, usage=SPEND, tags=tags, metadata={"model": "stub"})


@pytest.mark.parametrize("failing_call", ["update", "set_trace_io"])
def test_the_span_is_ended_even_when_the_sdk_rejects_a_call(failing_call: str) -> None:
    """A span left open is a Trace that never arrives. The failure still travels out to the
    boundary, which logs it; what it must not do is take the span's end with it."""
    root = FakeRoot(fails_on=failing_call)

    with pytest.raises(RuntimeError):
        finish(root)

    assert root.ended


def test_the_span_is_ended_when_the_tags_cannot_be_written() -> None:
    """The trace-level attributes are written through one private attribute of the SDK's span
    (see the adapter's module docstring). If a future version renames it, a Turn loses its
    tags — it does not lose its Trace."""
    root = RootWithoutAnOtelSpan()

    finish(root)

    assert root.ended


def test_the_tags_are_written_where_langfuse_reads_them() -> None:
    root = FakeRoot()

    finish(root, tags=("escalated", "language:es"))

    assert root._otel_span.attributes["langfuse.trace.tags"] == ["escalated", "language:es"]
    assert root._otel_span.attributes["langfuse.trace.name"] == "turn"


def test_nothing_is_written_to_a_span_that_is_no_longer_recording() -> None:
    """Past the end of a span the SDK ignores writes; asking first keeps the adapter honest
    about what it did rather than pretending the attributes landed."""
    silent = FakeOtelSpan(recording=False)
    root = FakeRoot(otel_span=silent)

    _set_trace_attributes(cast(LangfuseSpan, root), session_id="sess-0100")

    assert silent.attributes == {}
