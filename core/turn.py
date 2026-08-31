"""One Turn: a Visitor message in, a stream of chat events out.

The loop is hand-written rather than a framework's (ADR-0004): load the Session, build the
messages with the cached Knowledge Base block first, call the provider with the tool
definitions, run any tool calls in code, feed the results back, and stop — either because the
model stopped asking for tools, or because the iteration cap was reached.

`run` is around a hundred and seventy lines now, twice what it was when it only had to answer.
The half that grew is the four ways a Turn can end, because each one owes something different:
it completes and the Session is written and the Trace closed after the `done` event; the
Session's Turn cap is reached and nothing runs at all; the provider fails mid-answer and the
Visitor gets one safe sentence while the Trace keeps the spend and the half-written answer; or
the Visitor closes the tab, in which case nothing is stored and the Trace is the only record
there will ever be. Every one of those is a nested block a framework would have hidden and an
engineer would have had to guess at.

Everything that touches the outside world is a seam, so the whole loop runs offline against the
stub provider and the in-memory store, which is what the HTTP tests and the CI evals use.
"""

from collections.abc import AsyncIterator, Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from core.citations import split_citations
from core.events import ChatEvent, done_event, error_event, text_event, tool_event
from core.logging import current_request_id, get_logger
from core.prompt import SystemPrompt
from core.provider import (
    ModelMessage,
    ModelProvider,
    ProviderError,
    ProviderRequest,
    TextDelta,
    ToolCall,
    Usage,
)
from core.redaction import Redaction
from core.store import ConversationStore
from core.tools import ToolRegistry
from core.tracing import NoopTracer, Tracer, turn_tags

MAX_PROVIDER_ITERATIONS = 4
MAX_TURNS_PER_SESSION = 40

# What the Visitor reads when the model keeps asking for tools instead of answering. It is a
# dead end, so it ends in the one thing that always works.
GRACEFUL_STOP = (
    "I'm not getting to the bottom of that one. You can reach the team at hello@gocadre.ai "
    "or (619) 324-3223, and they will pick it up from here."
)

# What the Visitor reads when a Session has used up its Turn cap. It is the end of the
# conversation, so it hands over the two contact paths a Visitor can use unaided — the wording
# comes from the `contact` KB Section, and no phone script is invented for it.
SESSION_CLOSED = (
    "We have covered a lot in this conversation, and I have to stop here. To carry on, email "
    "hello@gocadre.ai or use the contact form at https://www.cadreai.com/contact, and the team "
    "will pick it up from where we left off."
)

# The only thing a Visitor is ever told about a provider failure. Whatever the provider said
# goes to the log, never to the browser: it is written for an engineer and may name a model,
# an account or a key.
PROVIDER_ERROR_MESSAGE = (
    "Something went wrong on my side and I couldn't finish that answer. Please try again — "
    "or reach the team at hello@gocadre.ai or (619) 324-3223."
)

logger = get_logger("turn")


def keep_as_is(message: str) -> Redaction:
    """The pre-model, pre-store hook, doing nothing — the identity for a Turn that wants no
    redaction at all. The composition root passes `core.redaction.refuse` in its place, and
    because there is one hook point applied at one call site, what the provider is sent and
    what the Session keeps can never drift apart."""
    return Redaction(message, {})


@dataclass(frozen=True)
class TurnRunner:
    """Runs a Turn against a `ModelProvider` and a `ConversationStore`."""

    provider: ModelProvider
    store: ConversationStore
    tools: ToolRegistry
    build_prompt: Callable[[], SystemPrompt]
    prepare_message: Callable[[str], Redaction] = keep_as_is
    # Where a Turn is observed. The default records nothing, so the loop is instrumented
    # unconditionally and a machine with no Langfuse keys runs the identical code path.
    tracer: Tracer = field(default_factory=NoopTracer)
    # Which model answered, for the Trace. The `ModelProvider` seam is deliberately silent
    # about model ids — an id is configuration, not something the loop decides — so the
    # composition root passes the one it selected.
    model: str = "unknown"
    max_iterations: int = field(default=MAX_PROVIDER_ITERATIONS)
    max_turns: int = field(default=MAX_TURNS_PER_SESSION)

    async def run(self, session_id: str, message: str) -> AsyncIterator[ChatEvent]:
        stored = await self.store.load(session_id)

        # A Session is not an open tab on the model. Past the cap the Visitor gets the closing
        # message and nothing else: no provider call, no write, so a stuck or automated
        # browser cannot keep spending.
        turns_taken = sum(1 for earlier in stored if earlier.role == "visitor")
        if turns_taken >= self.max_turns:
            # No Trace either: nothing ran. A closed Session made no provider call and wrote
            # nothing, and the one line worth reading about it is the log line above.
            logger.info("Session reached its Turn cap", extra={"turns_taken": turns_taken})
            yield text_event(SESSION_CLOSED)
            yield done_event(Usage())
            return

        prepared = self.prepare_message(message)
        visitor = ModelMessage(role="visitor", content=prepared.text)
        history = [*stored, visitor]

        prompt = self.build_prompt()
        answered: list[ModelMessage] = []
        usage = Usage()
        # The Trace is opened on the prepared message, not the raw one: the Refuse Set has
        # already gone, and what a Trace should show is what the model was actually sent. The
        # `full` profile runs at the tracing boundary on top of that (ADR-0006).
        trace = self.tracer.start_turn(
            session_id=session_id,
            request_id=current_request_id() or "",
            input_text=prepared.text,
        )
        tools_run: list[str] = []
        cited: dict[str, None] = {}
        language: str | None = None
        logger.info("Turn started", extra={"history_length": len(history)})
        # The one place a message body is logged, and only at debug level: what is written has
        # already lost the Refuse Set, and the formatter puts it through `full` on the way out,
        # so the Contact Details are tokenised as well (ADR-0006).
        logger.debug(
            "Visitor message", extra={"body": visitor.content, "redactions": dict(prepared.counts)}
        )

        # Declared out here because both endings a Turn can have without finishing — a
        # `ProviderError` and a Visitor closing the tab — need what was streamed but never
        # recorded in `answered`. It is emptied as soon as its text lands there, so what is
        # left is always exactly the part the Trace would otherwise lose.
        deltas: list[str] = []
        try:
            try:
                for iteration in range(self.max_iterations):
                    deltas = []
                    tool_calls: list[ToolCall] = []
                    call_usage = Usage()
                    request = ProviderRequest(
                        prompt, tuple(history), self.tools.definitions, session_id
                    )

                    with trace.provider_span(model=self.model, iteration=iteration) as span:
                        async for event in self.provider.stream(request):
                            match event:
                                case TextDelta():
                                    deltas.append(event.text)
                                    yield text_event(event.text)
                                case ToolCall():
                                    tool_calls.append(event)
                                case Usage():
                                    # Counted twice over, on purpose. The span reports this call
                                    # alone, so a Turn's cost breaks down by call rather than
                                    # making the last model call look like the expensive one; the
                                    # Turn's total is added to as each frame arrives, so a spend
                                    # already reported is not lost if the next frame is an error.
                                    call_usage = call_usage + event
                                    usage = usage + event
                        span.record_usage(usage=call_usage, output_text="".join(deltas))

                    assistant = ModelMessage("assistant", "".join(deltas), tuple(tool_calls))
                    deltas = []
                    history.append(assistant)
                    answered.append(assistant)
                    _remember(cited, split_citations(assistant.content)[1])
                    if not tool_calls:
                        break

                    for call in tool_calls:
                        yield tool_event(call.name, "started")
                        tools_run.append(call.name)
                        with trace.tool_span(name=call.name) as tool_run:
                            outcome = await self.tools.run(call, session_id)
                            tool_run.record_events(produced_events=bool(outcome.events))
                        for tool_output in outcome.events:
                            _remember(cited, tool_output.data.get("citations", ()))
                            language = language or tool_output.data.get("language")
                            yield tool_output
                        yield tool_event(call.name, "finished")
                        result = ModelMessage("tool", outcome.result, tool_call_id=call.id)
                        history.append(result)
                        answered.append(result)
                else:
                    logger.warning(
                        "Turn hit the iteration cap", extra={"iterations": len(answered)}
                    )
                    yield text_event(GRACEFUL_STOP)
                    answered.append(ModelMessage("assistant", GRACEFUL_STOP))
            except ProviderError as failure:
                logger.error("Turn failed", extra={"provider_error": failure.detail})
                yield error_event(PROVIDER_ERROR_MESSAGE)
                # A failed Turn is stored nowhere, so if it is not on the Trace it is nowhere at
                # all — and a Turn that failed is the first one an engineer goes looking for. The
                # provider's own words stay in the log line above: they are written for an
                # engineer and may name a model, an account or a key.
                trace.finish(
                    output_text=_answer(answered, "".join(deltas), failed=True),
                    usage=usage,
                    tags=turn_tags(
                        tools_run,
                        language=language,
                        provider_error=True,
                        redactions=prepared.counts,
                    ),
                    metadata=self._metadata(prepared, cited),
                )
                return

            # A Turn is stored when it completes, or not at all. Storing the Visitor message up
            # front would leave it behind whenever the Turn failed or the browser walked away
            # mid-stream, and the next Turn would send two Visitor messages back to back —
            # which is not a conversation any provider accepts.
            await self.store.append(session_id, [visitor, *answered])
            logger.info(
                "Turn finished",
                extra={
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "cached_tokens": usage.cached_tokens,
                    "cost_usd": usage.cost_usd,
                    # No trace id here: it is thirty-two hex characters, which is the shape of
                    # an API key, so the `full` profile writes it out as `[CREDENTIAL]` and it
                    # joins nothing. The join runs the other way — the Trace carries the
                    # `request_id` that every one of this Turn's log lines carries.
                },
            )
            yield done_event(usage, trace_id=trace.trace_id, redactions=prepared.counts)
            # After the `done` event, never before it: closing a Trace is an observability
            # vendor's work, and the Visitor's last frame does not wait behind it.
            trace.finish(
                output_text=_answer(answered),
                usage=usage,
                tags=turn_tags(tools_run, language=language, redactions=prepared.counts),
                metadata=self._metadata(prepared, cited),
            )
        except GeneratorExit:
            # The Visitor closed the tab: the server drops the stream and this generator is
            # closed where it stands. Nothing is written to the Session — the Turn did not
            # complete — so the Trace is the only record that any of this happened, and it is
            # closed here rather than left open, holding what the Visitor actually read.
            logger.info("Visitor left before the Turn finished")
            trace.finish(
                output_text=_answer(answered, "".join(deltas)),
                usage=usage,
                tags=turn_tags(
                    tools_run,
                    language=language,
                    redactions=prepared.counts,
                    disconnected=True,
                ),
                metadata=self._metadata(prepared, cited),
            )
            raise

    def _metadata(self, prepared: Redaction, cited: Mapping[str, None]) -> Mapping[str, Any]:
        """What a Trace carries besides its bodies: never a value, only counts and ids."""
        return {
            "model": self.model,
            "citations": list(cited),
            "redactions": dict(prepared.counts),
        }


def _remember(cited: dict[str, None], sections: Iterable[str]) -> None:
    """Collect KB Section ids in the order they were first cited, each one once."""
    for section in sections:
        cited[section] = None


def _answer(answered: Sequence[ModelMessage], partial: str = "", failed: bool = False) -> str:
    """What the Visitor was shown, which is what a Trace's output should be: the Assistant's
    words, whatever was still mid-sentence when the Turn ended early, and on a failed Turn the
    message that replaced the rest of them."""
    written = [message.content for message in answered if message.role == "assistant"]
    if partial:
        written.append(partial)
    if failed:
        written.append(PROVIDER_ERROR_MESSAGE)
    return "\n".join(part for part in written if part)
