"""The tools the Assistant may call, and how a call is executed.

Tools are plain functions over typed arguments (ADR-0004). A tool returns two things: the
result string the model reads on the next iteration, and the events the Visitor sees. Order is
fixed, because the tool definitions sit inside the prompt's cached prefix and re-serialising
them in a different order invalidates the cache for every Session (ADR-0001).
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from core.events import ChatEvent
from core.provider import ToolCall, ToolDefinition


@dataclass(frozen=True)
class ToolOutcome:
    """What running a tool produced: a result for the model, and events for the Visitor."""

    result: str
    events: tuple[ChatEvent, ...] = ()


@dataclass(frozen=True)
class Tool:
    definition: ToolDefinition
    run: Callable[[Mapping[str, Any]], ToolOutcome]


class ToolRegistry:
    def __init__(self, tools: Sequence[Tool]) -> None:
        self._tools = tuple(tools)
        self._by_name = {tool.definition.name: tool for tool in self._tools}

    @property
    def definitions(self) -> tuple[ToolDefinition, ...]:
        return tuple(tool.definition for tool in self._tools)

    def run(self, call: ToolCall) -> ToolOutcome:
        """Never raises: a hallucinated tool name or a malformed argument comes back to the
        model as a result it can correct, rather than ending the Visitor's Turn (ADR-0004)."""
        tool = self._by_name.get(call.name)
        if tool is None:
            return ToolOutcome(result=f"There is no tool named {call.name!r}.")
        try:
            return tool.run(call.arguments)
        except (KeyError, TypeError, ValueError) as rejected:
            return ToolOutcome(result=f"The call to {call.name!r} was rejected: {rejected}")
