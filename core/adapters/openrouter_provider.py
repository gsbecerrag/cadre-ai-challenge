"""The OpenRouter `ModelProvider` — the one production implementation of the seam (ADR-0002).

Raw HTTP against the OpenAI-compatible chat-completions endpoint, no vendor SDK (ADR-0004),
because everything interesting about this integration is a detail an SDK would hide:

- the system prompt is sent as two content parts with an explicit `cache_control` breakpoint on
  the first, so the Knowledge Base prefix is cached and the volatile tail is not (ADR-0001);
- a streamed tool call arrives as fragments — the id and name once, the arguments a few
  characters at a time — and has to be reassembled by index before it is anything;
- a failure can arrive *after* HTTP 200, as a chunk with `finish_reason: "error"`, when the
  Visitor is already reading the answer;
- the cost of the Turn is the provider's own number from the final usage chunk, never a
  price-table estimate.

Nothing here decides what to do about any of that: a failure becomes `ProviderError` and the
Turn loop decides what the Visitor sees.
"""

import json
from collections.abc import AsyncIterator, Iterator, Mapping, Sequence
from typing import Any

import httpx2

from core.logging import get_logger
from core.provider import (
    ModelMessage,
    ProviderError,
    ProviderEvent,
    ProviderRequest,
    TextDelta,
    ToolCall,
    ToolDefinition,
    Usage,
)

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
CHAT_COMPLETIONS = "/chat/completions"
STREAM_DONE = "[DONE]"

# An answer streams for as long as the model writes, so the read budget is generous; a
# connection that never opens is a fast failure.
TIMEOUT = httpx2.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0)

# Statuses where trying again could plausibly work. Nothing retries today (the Turn loop
# reports the failure); the flag is what a retry would read.
RETRYABLE_STATUSES = frozenset({408, 409, 425, 429, 500, 502, 503, 504})

# The Visitor never reads this — the Turn loop substitutes its own wording — but a
# `ProviderError` may reach a Visitor in principle, so it stays safe to show.
UNAVAILABLE = "I couldn't reach the model just now."

logger = get_logger("openrouter")


class OpenRouterModelProvider:
    """Streams one model call over OpenRouter's chat-completions API."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        app_url: str = "",
        app_name: str = "",
        cache_ttl: str = "1h",
        base_url: str = DEFAULT_BASE_URL,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> None:
        self._model = model
        self._cache_ttl = cache_ttl
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        if app_url:
            # Attribution. The title is only honoured alongside the referer, so they travel
            # together or not at all.
            headers["HTTP-Referer"] = app_url
            headers["X-OpenRouter-Title"] = app_name or "Cadre AI Support Agent"
        self._client = httpx2.AsyncClient(
            base_url=base_url,
            headers=headers,
            timeout=TIMEOUT,
            transport=transport,
        )

    async def stream(self, request: ProviderRequest) -> AsyncIterator[ProviderEvent]:
        payload = self.build_payload(request)
        pending = _PendingToolCalls()
        try:
            async with self._client.stream("POST", CHAT_COMPLETIONS, json=payload) as response:
                if response.status_code >= 400:
                    await response.aread()
                    raise _rejected(response)
                async for event in httpx2.EventSource(response):
                    if event.data == STREAM_DONE:
                        break
                    for produced in _events_of(_decode(event.data), pending):
                        yield produced
        except httpx2.HTTPError as unreachable:
            # Connect failures, read timeouts, and a body that is not the event stream the
            # content type promised.
            raise ProviderError(
                UNAVAILABLE,
                detail=f"{type(unreachable).__name__}: {unreachable}",
                retryable=True,
            ) from unreachable
        # A stream that stops before any finish_reason still leaves its tool calls complete
        # enough to run; anything half-written is dropped by the assembler.
        for call in pending.drain():
            yield call

    def build_payload(self, request: ProviderRequest) -> dict[str, Any]:
        """The request body, built where it can be read in a test rather than on the wire."""
        payload: dict[str, Any] = {
            "model": self._model,
            "stream": True,
            # Deprecated in favour of usage always being returned, and sent anyway: it costs
            # nothing and the Turn's cost is not a field to discover missing in production.
            "usage": {"include": True},
            "messages": [
                self._system_message(request),
                *(_wire_message(message) for message in request.messages),
            ],
        }
        if request.tools:
            # Every call in the tool loop carries the definitions; OpenRouter validates the
            # schema per request, not per conversation.
            payload["tools"] = [_wire_tool(tool) for tool in request.tools]
        if request.session_id:
            # Sticky routing: the next Turn of this Session reaches the upstream that holds
            # its cached prefix (ADR-0002).
            payload["session_id"] = request.session_id
        return payload

    def _system_message(self, request: ProviderRequest) -> dict[str, Any]:
        """One system message, split at the cache breakpoint the prompt already carries."""
        return {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": request.prompt.cached,
                    "cache_control": {"type": "ephemeral", "ttl": self._cache_ttl},
                },
                {"type": "text", "text": request.prompt.volatile},
            ],
        }


class _PendingToolCalls:
    """Tool-call fragments, gathered by index until the model stops writing them.

    The id and the name arrive once, on the first fragment; the arguments arrive as a JSON
    string a few characters at a time. Nothing is a `ToolCall` until it is whole.
    """

    def __init__(self) -> None:
        self._slots: dict[int, dict[str, str]] = {}

    def add(self, fragments: Sequence[Mapping[str, Any]]) -> None:
        for fragment in fragments:
            slot = self._slots.setdefault(
                int(fragment.get("index", 0)), {"id": "", "name": "", "arguments": ""}
            )
            slot["id"] = fragment.get("id") or slot["id"]
            function = fragment.get("function") or {}
            slot["name"] = function.get("name") or slot["name"]
            slot["arguments"] += function.get("arguments") or ""

    def drain(self) -> list[ToolCall]:
        calls = [
            ToolCall(id=slot["id"], name=slot["name"], arguments=_arguments(slot))
            for _index, slot in sorted(self._slots.items())
            if slot["name"]
        ]
        self._slots.clear()
        return calls


def _arguments(slot: Mapping[str, str]) -> Mapping[str, Any]:
    """A tool call whose arguments are not JSON is still a tool call.

    The registry answers a call with missing arguments with an error result the model can
    correct on the next iteration, which is a better Turn than a crash (ADR-0004).
    """
    written = slot["arguments"].strip()
    if not written:
        return {}
    try:
        parsed = json.loads(written)
    except json.JSONDecodeError:
        logger.warning("Tool call arguments were not JSON", extra={"tool": slot["name"]})
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _decode(data: str) -> Mapping[str, Any]:
    try:
        chunk = json.loads(data)
    except json.JSONDecodeError as malformed:
        raise ProviderError(
            UNAVAILABLE, detail=f"Malformed stream chunk: {malformed}", retryable=True
        ) from malformed
    if not isinstance(chunk, dict):
        raise ProviderError(UNAVAILABLE, detail="Stream chunk was not an object")
    return chunk


def _events_of(chunk: Mapping[str, Any], pending: _PendingToolCalls) -> Iterator[ProviderEvent]:
    """The provider events one chunk produces, in the order the Turn loop expects them."""
    choices = chunk.get("choices") or [{}]
    choice = choices[0]
    finish_reason = choice.get("finish_reason")

    # A failed generation arrives on a successful HTTP status, possibly after some of the
    # answer has already been streamed to the browser.
    if chunk.get("error") or finish_reason == "error":
        raise _failed(chunk)

    delta = choice.get("delta") or {}
    if delta.get("content"):
        yield TextDelta(delta["content"])
    if delta.get("tool_calls"):
        pending.add(delta["tool_calls"])
    if finish_reason:
        yield from pending.drain()

    usage = chunk.get("usage")
    if usage:
        cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
        yield Usage(
            input_tokens=usage.get("prompt_tokens") or 0,
            output_tokens=usage.get("completion_tokens") or 0,
            cached_tokens=cached,
            cost_usd=usage.get("cost") or 0.0,
        )


def _failed(chunk: Mapping[str, Any]) -> ProviderError:
    error = chunk.get("error") or {}
    code = error.get("code", "error")
    message = error.get("message", "the provider ended the stream with finish_reason 'error'")
    return ProviderError(
        UNAVAILABLE,
        detail=f"Mid-stream failure {code}: {message}",
        retryable=str(code) != "400",
    )


def _rejected(response: httpx2.Response) -> ProviderError:
    """A pre-stream failure: an ordinary JSON error body on a 4xx or 5xx."""
    try:
        body = response.json()
        message = (body.get("error") or {}).get("message") or response.text
    except ValueError:
        message = response.text
    return ProviderError(
        UNAVAILABLE,
        detail=f"HTTP {response.status_code} from OpenRouter: {message}"[:500],
        retryable=response.status_code in RETRYABLE_STATUSES,
    )


def _wire_message(message: ModelMessage) -> dict[str, Any]:
    """Our vocabulary on the wire: a Visitor speaks as OpenAI's `user`."""
    if message.role == "tool":
        return {
            "role": "tool",
            "tool_call_id": message.tool_call_id,
            "content": message.content,
        }
    if message.role == "assistant":
        wire: dict[str, Any] = {"role": "assistant", "content": message.content or None}
        if message.tool_calls:
            wire["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": json.dumps(dict(call.arguments)),
                    },
                }
                for call in message.tool_calls
            ]
        return wire
    return {"role": "user", "content": message.content}


def _wire_tool(tool: ToolDefinition) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": dict(tool.parameters),
        },
    }
