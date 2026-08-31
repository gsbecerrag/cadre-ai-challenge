"""The tools the Assistant may call, and how a call is executed.

Tools are plain functions over typed arguments (ADR-0004). A tool returns two things: the
result string the model reads on the next iteration, and the events the Visitor sees. Order is
fixed, because the tool definitions sit inside the prompt's cached prefix and re-serialising
them in a different order invalidates the cache for every Session (ADR-0001).

A tool is called with the Session id and awaited, because a tool that writes writes for one
Session: `capture_lead` (ticket 09) reads and writes that Session's Lead through the
`ConversationStore`, which is async like everything else that leaves the process. A tool with
nothing to store — `escalate` — simply ignores the id.
"""

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from core.events import ChatEvent
from core.logging import get_logger
from core.provider import ToolCall, ToolDefinition

logger = get_logger("tools")


@dataclass(frozen=True)
class ToolOutcome:
    """What running a tool produced: a result for the model, and events for the Visitor."""

    result: str
    events: tuple[ChatEvent, ...] = ()


# The arguments the model sent, and the Session the Turn belongs to.
ToolRun = Callable[[Mapping[str, Any], str], Awaitable[ToolOutcome]]


@dataclass(frozen=True)
class Tool:
    definition: ToolDefinition
    run: ToolRun


class ToolRegistry:
    def __init__(self, tools: Sequence[Tool]) -> None:
        self._tools = tuple(tools)
        self._by_name = {tool.definition.name: tool for tool in self._tools}

    @property
    def definitions(self) -> tuple[ToolDefinition, ...]:
        return tuple(tool.definition for tool in self._tools)

    async def run(self, call: ToolCall, session_id: str) -> ToolOutcome:
        """Never raises: a hallucinated tool name or a malformed argument comes back to the
        model as a result it can correct, rather than ending the Visitor's Turn (ADR-0004).

        The Session id is required rather than defaulted: a tool that writes writes for one
        Session, and a caller that forgot it would file every Lead under the same empty id.
        """
        tool = self._by_name.get(call.name)
        if tool is None:
            return ToolOutcome(result=f"There is no tool named {call.name!r}.")
        try:
            return await tool.run(call.arguments, session_id)
        except Exception as rejected:
            # Broad on purpose: whatever a tool manages to raise, the Visitor's Turn carries
            # on. The traceback goes to the log, and the model gets something it can act on.
            logger.exception("Tool call failed", extra={"tool": call.name})
            return ToolOutcome(result=f"The call to {call.name!r} was rejected: {rejected}")
