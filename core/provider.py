"""The `ModelProvider` seam: what the Assistant needs from a model, and nothing more.

One production implementation (OpenRouter, ticket 03) and one test implementation (the
scriptable stub) sit behind this. The vocabulary is ours, not the provider's: a message from a
Visitor has role `visitor`, and mapping that to whatever wire format an API wants — `user` for
the OpenAI shape — is the adapter's job (docs/design/README.md ruling).
"""

from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from core.prompt import SystemPrompt

MessageRole = Literal["visitor", "assistant", "tool"]


@dataclass(frozen=True)
class ToolCall:
    """The model asking for a tool to be run, with its arguments already parsed."""

    id: str
    name: str
    arguments: Mapping[str, Any]


@dataclass(frozen=True)
class ModelMessage:
    """One message in a Session's history, in the shape the loop and the store both use."""

    role: MessageRole
    content: str
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None


@dataclass(frozen=True)
class ToolDefinition:
    """A tool as the model sees it. Serialised in a fixed order so the cache stays warm."""

    name: str
    description: str
    parameters: Mapping[str, Any]


@dataclass(frozen=True)
class TextDelta:
    """A fragment of the answer, forwarded to the browser as it arrives."""

    text: str


@dataclass(frozen=True)
class Usage:
    """What the Turn cost. Read from the provider's final usage chunk, never estimated."""

    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    cost_usd: float = 0.0

    def __add__(self, other: "Usage") -> "Usage":
        """A Turn may take several provider calls; the Visitor is quoted their total."""
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cached_tokens=self.cached_tokens + other.cached_tokens,
            cost_usd=self.cost_usd + other.cost_usd,
        )


ProviderEvent = TextDelta | ToolCall | Usage


class ProviderError(RuntimeError):
    """A model call that cannot be completed.

    Carries a message that is safe to show a Visitor, because the failure may arrive halfway
    through a streamed answer and there is nowhere else for it to go. Provider detail belongs
    in `detail`, which is logged and never streamed.
    """

    def __init__(self, message: str, *, detail: str = "", retryable: bool = False) -> None:
        super().__init__(detail or message)
        self.message = message
        self.detail = detail or message
        self.retryable = retryable


@dataclass(frozen=True)
class ProviderRequest:
    """Everything one model call needs. The prompt arrives split at its cache breakpoint."""

    prompt: SystemPrompt
    messages: tuple[ModelMessage, ...]
    tools: tuple[ToolDefinition, ...] = ()
    # Which Session this call belongs to. The adapter passes it to the provider for sticky
    # routing, so consecutive Turns reach the upstream that already holds the cached prefix
    # (ADR-0002). It is an opaque id, never anything about the Visitor.
    session_id: str = ""
    # A JSON schema the answer must satisfy, in the provider's `response_format` shape, or
    # `None` for the ordinary case of prose. The Assistant never asks for one — a Visitor
    # reads sentences — but the Triage Agent does (ADR-0005), and enforcing the shape at the
    # provider beats parsing it back out of prose the model was only asked nicely for.
    response_format: Mapping[str, Any] | None = None


class ModelProvider(Protocol):
    """Streams a model's answer as text deltas, tool calls, and one usage block."""

    def stream(self, request: ProviderRequest) -> AsyncIterator[ProviderEvent]:
        """Yield the model's output in order, or raise `ProviderError`."""
        ...
