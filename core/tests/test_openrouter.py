"""The OpenRouter `ModelProvider` — seam S2, over recorded streams and no network.

Two of the three fixtures under `fixtures/openrouter/` are recordings of real responses from
`anthropic/claude-sonnet-5`, kept because the documentation does not spell out how a streamed
tool call is fragmented; the mid-stream error is hand-written from the shape OpenRouter's
streaming page documents (HTTP 200, a top-level `error`, `finish_reason: "error"`).

The transport is a stand-in, so these tests also read the request the adapter builds: the
cache marker on the system block and the attribution headers are wire contracts, and getting
either wrong is silent — a doubled bill, or spend attributed to nobody.
"""

import asyncio
import json
from collections.abc import Callable
from pathlib import Path

import httpx2
import pytest

from core.adapters.openrouter_provider import OpenRouterModelProvider
from core.prompt import SystemPrompt
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

FIXTURES = Path(__file__).parent / "fixtures" / "openrouter"

# Obviously fake: no test may hold a usable key.
API_KEY = "sk-or-v1-not-a-real-key"
APP_URL = "https://support.example.com"
APP_NAME = "Cadre AI Support Agent"
MODEL = "anthropic/claude-sonnet-5"

CACHED_PROMPT = "You are the Cadre AI Assistant.\n\nKnowledge Base:\n\n[services#what] ..."
VOLATILE_PROMPT = "Today's date is 2026-08-31."

PROMPT = SystemPrompt(
    cached_sections=(("identity", CACHED_PROMPT),),
    volatile=VOLATILE_PROMPT,
)

ESCALATE = ToolDefinition(
    name="escalate",
    description="Record an Escalation and show the Visitor one concrete next step.",
    parameters={
        "type": "object",
        "properties": {"reason": {"type": "string"}, "next_step": {"type": "string"}},
        "required": ["reason", "next_step"],
    },
)

# What the recorded answer stream says, assembled.
RECORDED_ANSWER = (
    "Cadre AI is an AI strategy and implementation consultancy [services#what-cadre-does]."
)
RECORDED_USAGE = Usage(input_tokens=104, output_tokens=34, cached_tokens=0, cost_usd=0.000548)

# What the recorded tool-call stream asks for, assembled across nineteen argument fragments.
RECORDED_TOOL_CALL = ToolCall(
    id="toolu_01Bm6uZUuEd9p3MG3i6Tbatk",
    name="escalate",
    arguments={
        "reason": "The Knowledge Base does not include pricing information for Cadre AI "
        "engagements.",
        "next_step": "Please contact the Cadre AI sales team directly (via the official "
        "contact form or sales email on the Cadre AI website) to request a customized "
        "pricing quote for your engagement.",
    },
)


def a_request(*messages: ModelMessage) -> ProviderRequest:
    visitor = messages or (ModelMessage("visitor", "What does Cadre AI do?"),)
    return ProviderRequest(prompt=PROMPT, messages=visitor, tools=(ESCALATE,), session_id="s-01")


def replaying(fixture: str) -> Callable[[httpx2.Request], httpx2.Response]:
    """A transport handler that answers with a recorded stream."""
    body = (FIXTURES / fixture).read_bytes()

    def handle(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, content=body, headers={"content-type": "text/event-stream"})

    return handle


def provider_over(
    handle: Callable[[httpx2.Request], httpx2.Response],
) -> OpenRouterModelProvider:
    return OpenRouterModelProvider(
        api_key=API_KEY,
        model=MODEL,
        app_url=APP_URL,
        app_name=APP_NAME,
        cache_ttl="1h",
        transport=httpx2.MockTransport(handle),
    )


def stream(provider: OpenRouterModelProvider, request: ProviderRequest) -> list[ProviderEvent]:
    async def collect() -> list[ProviderEvent]:
        return [event async for event in provider.stream(request)]

    return asyncio.run(collect())


def stream_until_failure(
    provider: OpenRouterModelProvider, request: ProviderRequest
) -> tuple[list[ProviderEvent], ProviderError]:
    async def collect() -> tuple[list[ProviderEvent], ProviderError]:
        events: list[ProviderEvent] = []
        try:
            async for event in provider.stream(request):
                events.append(event)
        except ProviderError as failure:
            return events, failure
        raise AssertionError("the stream ended without a ProviderError")

    return asyncio.run(collect())


def test_a_recorded_answer_stream_yields_its_text_and_the_usage_of_the_final_chunk() -> None:
    events = stream(provider_over(replaying("answer-with-usage.sse")), a_request())

    text = "".join(event.text for event in events if isinstance(event, TextDelta))
    assert text == RECORDED_ANSWER
    assert events[-1] == RECORDED_USAGE


def test_a_recorded_tool_call_is_assembled_from_its_fragments_with_parsed_arguments() -> None:
    events = stream(provider_over(replaying("tool-call.sse")), a_request())

    calls = [event for event in events if isinstance(event, ToolCall)]
    assert calls == [RECORDED_TOOL_CALL]
    assert events[-1] == Usage(
        input_tokens=713, output_tokens=133, cached_tokens=0, cost_usd=0.002756
    )


def test_a_mid_stream_error_on_a_successful_status_becomes_a_provider_error() -> None:
    """The failure arrives as HTTP 200 with `finish_reason: "error"`, halfway through an
    answer the Visitor is already reading."""
    events, failure = stream_until_failure(
        provider_over(replaying("mid-stream-error.sse")), a_request()
    )

    assert events == [TextDelta("Let me check that")]
    assert "Provider returned error" in failure.detail
    assert "502" in failure.detail


def test_a_rejected_request_becomes_a_provider_error_naming_the_status() -> None:
    def rate_limited(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(429, json={"error": {"code": 429, "message": "Rate limited"}})

    _events, failure = stream_until_failure(provider_over(rate_limited), a_request())

    assert "429" in failure.detail
    assert failure.retryable


def test_a_transport_timeout_becomes_a_provider_error() -> None:
    def times_out(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadTimeout("timed out", request=request)

    _events, failure = stream_until_failure(provider_over(times_out), a_request())

    assert "timed out" in failure.detail
    assert failure.retryable


def test_the_system_prompt_is_sent_as_one_cacheable_block_with_the_configured_ttl() -> None:
    """The Knowledge Base is the whole prefix (ADR-0001). Without the marker every Turn pays
    full input price for it; with the marker inside the volatile tail it would never hit."""
    seen: list[httpx2.Request] = []

    def capture(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return replaying("answer-with-usage.sse")(request)

    stream(provider_over(capture), a_request())

    body = json.loads(seen[0].content)
    system = body["messages"][0]
    assert system["role"] == "system"
    assert system["content"] == [
        {
            "type": "text",
            "text": PROMPT.cached,
            "cache_control": {"type": "ephemeral", "ttl": "1h"},
        },
        {"type": "text", "text": VOLATILE_PROMPT},
    ]


def test_the_request_names_the_model_the_tools_and_the_session_it_belongs_to() -> None:
    seen: list[httpx2.Request] = []

    def capture(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return replaying("answer-with-usage.sse")(request)

    stream(provider_over(capture), a_request())

    body = json.loads(seen[0].content)
    assert body["model"] == MODEL
    assert body["stream"] is True
    # The tool list goes on every call in the loop, not only the first: OpenRouter validates
    # the schema per request.
    assert body["tools"] == [
        {
            "type": "function",
            "function": {
                "name": "escalate",
                "description": ESCALATE.description,
                "parameters": dict(ESCALATE.parameters),
            },
        }
    ]
    # Sticky routing: consecutive Turns of a Session reach the upstream holding its cache.
    assert body["session_id"] == "s-01"


def test_the_request_identifies_the_app_to_openrouter() -> None:
    seen: list[httpx2.Request] = []

    def capture(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return replaying("answer-with-usage.sse")(request)

    stream(provider_over(capture), a_request())

    headers = seen[0].headers
    assert headers["authorization"] == f"Bearer {API_KEY}"
    assert headers["http-referer"] == APP_URL
    assert headers["x-openrouter-title"] == APP_NAME


def test_a_visitor_speaks_as_a_user_and_a_tool_result_carries_its_call_id() -> None:
    """`visitor` is our word for the role; the wire wants OpenAI's."""
    seen: list[httpx2.Request] = []

    def capture(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return replaying("answer-with-usage.sse")(request)

    conversation = (
        ModelMessage("visitor", "What does it cost?"),
        ModelMessage("assistant", "", tool_calls=(RECORDED_TOOL_CALL,)),
        ModelMessage("tool", "Escalation recorded.", tool_call_id=RECORDED_TOOL_CALL.id),
    )
    stream(provider_over(capture), a_request(*conversation))

    body = json.loads(seen[0].content)
    assert body["messages"][1:] == [
        {"role": "user", "content": "What does it cost?"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": RECORDED_TOOL_CALL.id,
                    "type": "function",
                    "function": {
                        "name": "escalate",
                        "arguments": json.dumps(dict(RECORDED_TOOL_CALL.arguments)),
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": RECORDED_TOOL_CALL.id,
            "content": "Escalation recorded.",
        },
    ]


def test_an_unparsable_tool_argument_string_is_not_a_crash() -> None:
    """A model that streams broken JSON must not end the Turn; the loop can hand the model
    an error result and let it correct itself (ADR-0004)."""
    broken = (
        'data: {"choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"id":"call-1",'
        '"type":"function","function":{"name":"escalate","arguments":"{not json"}}]},'
        '"finish_reason":"tool_calls"}]}\n\ndata: [DONE]\n\n'
    )

    def half_written(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200, content=broken.encode(), headers={"content-type": "text/event-stream"}
        )

    events = stream(provider_over(half_written), a_request())

    assert events == [ToolCall(id="call-1", name="escalate", arguments={})]


@pytest.mark.parametrize("ttl", ["5m", "1h"])
def test_the_cache_ttl_is_configuration_not_a_constant(ttl: str) -> None:
    seen: list[httpx2.Request] = []

    def capture(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return replaying("answer-with-usage.sse")(request)

    provider = OpenRouterModelProvider(
        api_key=API_KEY,
        model=MODEL,
        app_url=APP_URL,
        app_name=APP_NAME,
        cache_ttl=ttl,
        transport=httpx2.MockTransport(capture),
    )
    stream(provider, a_request())

    body = json.loads(seen[0].content)
    assert body["messages"][0]["content"][0]["cache_control"]["ttl"] == ttl
