"""The events a Turn streams to the browser, and their payloads.

This is the contract the chat widget's reducer reduces. Every event the spec names exists here
from the start, even where the Turn cannot emit it yet, so that the reducer, the API and the
later tickets are all written against one shape: `card` is filled in by ticket 08, `offer` and
`handover` by ticket 11, and `done.trace_id` stops being null in ticket 06.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from core.provider import Usage

ChatEventName = Literal[
    "text",
    "tool",
    "card",
    "escalation",
    "offer",
    "handover",
    "done",
    "error",
]

ToolStatus = Literal["started", "finished"]
HandoverMode = Literal["video", "callback"]


@dataclass(frozen=True)
class ChatEvent:
    """One named event with a JSON payload, ready to be framed as Server-Sent Events."""

    name: ChatEventName
    data: Mapping[str, Any]


def text_event(delta: str) -> ChatEvent:
    """A fragment of the Assistant's answer, including any `[topic#heading]` markers."""
    return ChatEvent("text", {"delta": delta})


def tool_event(name: str, status: ToolStatus) -> ChatEvent:
    """A marker so the Visitor sees that something is happening, not a frozen bubble."""
    return ChatEvent("tool", {"name": name, "status": status})


def card_event(
    title: str,
    steps: Sequence[str],
    destination: str,
    citations: Sequence[str] = (),
) -> ChatEvent:
    """A Walkthrough Card: the steps and the destination. Ticket 08 emits it."""
    return ChatEvent(
        "card",
        {
            "title": title,
            "steps": list(steps),
            "destination": destination,
            "citations": list(citations),
        },
    )


def escalation_event(
    title: str,
    body: str,
    next_step: str,
    citations: Sequence[str] = (),
) -> ChatEvent:
    """An Escalation: what is known, what cannot be confirmed, one concrete next step."""
    return ChatEvent(
        "escalation",
        {
            "title": title,
            "body": body,
            "next_step": next_step,
            "citations": list(citations),
        },
    )


def offer_event(request_id: str, prompt: str) -> ChatEvent:
    """The offer of a Hand-over, made at most once per Session. Ticket 11 emits it."""
    return ChatEvent("offer", {"request_id": request_id, "prompt": prompt})


def handover_event(request_id: str, state: str, mode: HandoverMode) -> ChatEvent:
    """A Handover Request changing state. Ticket 11 emits it."""
    return ChatEvent("handover", {"request_id": request_id, "state": state, "mode": mode})


def done_event(usage: Usage, trace_id: str | None = None) -> ChatEvent:
    """The Turn is complete. `trace_id` stays null until Langfuse arrives in ticket 06."""
    return ChatEvent(
        "done",
        {
            "trace_id": trace_id,
            "usage": {
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cached_tokens": usage.cached_tokens,
                "cost_usd": usage.cost_usd,
            },
        },
    )


def error_event(message: str) -> ChatEvent:
    """The Turn failed. The message is written for a Visitor: never a stack trace, never a
    provider's own wording, never an id or a key."""
    return ChatEvent("error", {"message": message})
