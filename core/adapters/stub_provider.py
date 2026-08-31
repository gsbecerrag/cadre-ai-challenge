"""The scriptable `ModelProvider` — the whole conversation pipeline with no network.

A script is keyed by the last Visitor message and holds one response per iteration of the tool
loop, so a test can say "first ask for a tool, then answer". Past the end of a script the last
response repeats, which is how the iteration cap is exercised. A `ProviderError` placed in a
response is raised where it sits, so a mid-stream failure can be scripted after some text has
already reached the browser — which is how the real failure arrives (ADR-0004).
"""

import asyncio
from collections.abc import AsyncIterator, Mapping, Sequence

from core.provider import ModelMessage, ProviderError, ProviderEvent, ProviderRequest

StubEvent = ProviderEvent | ProviderError
StubResponse = Sequence[StubEvent]
StubScript = tuple[tuple[StubEvent, ...], ...]

NOTHING_SCRIPTED = "The stub provider has no script for this Visitor message."


def _freeze(responses: Sequence[StubResponse]) -> StubScript:
    return tuple(tuple(response) for response in responses)


def _last_visitor_message(messages: Sequence[ModelMessage]) -> str:
    for message in reversed(messages):
        if message.role == "visitor":
            return message.content
    return ""


def _iteration(messages: Sequence[ModelMessage]) -> int:
    """Which pass of the tool loop this is, read off the messages rather than kept as state:
    every completed pass leaves one Assistant message after the Visitor's."""
    for index, message in enumerate(reversed(messages)):
        if message.role == "visitor":
            tail = messages[len(messages) - index :]
            return sum(1 for message in tail if message.role == "assistant")
    return 0


class StubModelProvider:
    def __init__(
        self,
        scripts: Mapping[str, Sequence[StubResponse]] | None = None,
        fallback: Sequence[StubResponse] | None = None,
        delay_seconds: float = 0.0,
    ) -> None:
        self._scripts = {
            trigger.casefold(): _freeze(responses) for trigger, responses in (scripts or {}).items()
        }
        # An unscripted Visitor message is a test that forgot to say what the model does,
        # so it fails loudly rather than streaming an empty answer.
        self._fallback = _freeze(fallback) if fallback else ((ProviderError(NOTHING_SCRIPTED),),)
        # A pause between deltas so `make dev` shows an answer arriving, not appearing. Tests
        # leave it at zero.
        self._delay_seconds = delay_seconds
        self.requests: list[ProviderRequest] = []

    def script(self, trigger: str, *responses: StubResponse) -> None:
        """Answer any Visitor message containing `trigger` with these responses, in order."""
        self._scripts[trigger.casefold()] = _freeze(responses)

    @property
    def calls(self) -> int:
        """How many times the provider was asked for a completion, across every Turn."""
        return len(self.requests)

    def _script_for(self, message: str) -> StubScript:
        haystack = message.casefold()
        matches = [
            (trigger, script)
            for trigger, script in self._scripts.items()
            if trigger and trigger in haystack
        ]
        if not matches:
            return self._fallback
        # The most specific trigger wins, so adding a narrower script never silently
        # reinterprets an existing one.
        _trigger, script = max(matches, key=lambda match: len(match[0]))
        return script

    async def stream(self, request: ProviderRequest) -> AsyncIterator[ProviderEvent]:
        self.requests.append(request)
        script = self._script_for(_last_visitor_message(request.messages))
        # Past the end of the script the last response repeats: a model that keeps asking for
        # tools is exactly the case the iteration cap exists for.
        response = script[min(_iteration(request.messages), len(script) - 1)]
        for event in response:
            if isinstance(event, ProviderError):
                raise event
            if self._delay_seconds:
                await asyncio.sleep(self._delay_seconds)
            yield event
