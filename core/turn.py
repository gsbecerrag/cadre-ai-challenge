"""One Turn: a Visitor message in, a stream of chat events out.

The loop is hand-written and about eighty lines on purpose (ADR-0004): load the Session, build
the messages with the cached Knowledge Base block first, call the provider with the tool
definitions, run any tool calls in code, feed the results back, and stop — either because the
model stopped asking for tools, or because the iteration cap was reached.

Everything that touches the outside world is a seam, so the whole loop runs offline against the
stub provider and the in-memory store, which is what the HTTP tests and the CI evals use.
"""

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field

from core.events import ChatEvent, done_event, error_event, text_event, tool_event
from core.logging import get_logger
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
from core.store import ConversationStore
from core.tools import ToolRegistry

MAX_PROVIDER_ITERATIONS = 4

# What the Visitor reads when the model keeps asking for tools instead of answering. It is a
# dead end, so it ends in the one thing that always works.
GRACEFUL_STOP = (
    "I'm not getting to the bottom of that one. You can reach the team at hello@gocadre.ai "
    "or (619) 324-3223, and they will pick it up from here."
)

# The only thing a Visitor is ever told about a provider failure. Whatever the provider said
# goes to the log, never to the browser: it is written for an engineer and may name a model,
# an account or a key.
PROVIDER_ERROR_MESSAGE = (
    "Something went wrong on my side and I couldn't finish that answer. Please try again — "
    "or reach the team at hello@gocadre.ai or (619) 324-3223."
)

logger = get_logger("turn")


def keep_as_is(message: str) -> str:
    """The pre-model, pre-store hook, doing nothing. Ticket 05 plugs the redactor in here so
    that the Refuse Set is stripped before the provider sees the message and before it is
    stored — one hook point, so the two can never drift apart."""
    return message


@dataclass(frozen=True)
class TurnRunner:
    """Runs a Turn against a `ModelProvider` and a `ConversationStore`."""

    provider: ModelProvider
    store: ConversationStore
    tools: ToolRegistry
    build_prompt: Callable[[], SystemPrompt]
    prepare_message: Callable[[str], str] = keep_as_is
    max_iterations: int = field(default=MAX_PROVIDER_ITERATIONS)

    async def run(self, session_id: str, message: str) -> AsyncIterator[ChatEvent]:
        visitor = ModelMessage(role="visitor", content=self.prepare_message(message))
        history = [*await self.store.load(session_id), visitor]

        prompt = self.build_prompt()
        answered: list[ModelMessage] = []
        usage = Usage()
        logger.info("Turn started", extra={"history_length": len(history)})

        try:
            for _iteration in range(self.max_iterations):
                deltas: list[str] = []
                tool_calls: list[ToolCall] = []
                request = ProviderRequest(prompt, tuple(history), self.tools.definitions)

                async for event in self.provider.stream(request):
                    match event:
                        case TextDelta():
                            deltas.append(event.text)
                            yield text_event(event.text)
                        case ToolCall():
                            tool_calls.append(event)
                        case Usage():
                            usage = usage + event

                assistant = ModelMessage("assistant", "".join(deltas), tuple(tool_calls))
                history.append(assistant)
                answered.append(assistant)
                if not tool_calls:
                    break

                for call in tool_calls:
                    yield tool_event(call.name, "started")
                    outcome = self.tools.run(call)
                    for tool_output in outcome.events:
                        yield tool_output
                    yield tool_event(call.name, "finished")
                    result = ModelMessage("tool", outcome.result, tool_call_id=call.id)
                    history.append(result)
                    answered.append(result)
            else:
                logger.warning("Turn hit the iteration cap", extra={"iterations": len(answered)})
                yield text_event(GRACEFUL_STOP)
                answered.append(ModelMessage("assistant", GRACEFUL_STOP))
        except ProviderError as failure:
            logger.error("Turn failed", extra={"provider_error": failure.detail})
            yield error_event(PROVIDER_ERROR_MESSAGE)
            return

        # A Turn is stored when it completes, or not at all. Storing the Visitor message up
        # front would leave it behind whenever the Turn failed or the browser walked away
        # mid-stream, and the next Turn would send two Visitor messages back to back — which
        # is not a conversation any provider accepts.
        await self.store.append(session_id, [visitor, *answered])
        logger.info(
            "Turn finished",
            extra={
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cached_tokens": usage.cached_tokens,
                "cost_usd": usage.cost_usd,
            },
        )
        yield done_event(usage)
