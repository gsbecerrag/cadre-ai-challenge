"""The events a Turn streams to the browser, and their payloads.

This is the contract the chat widget's reducer reduces. Every event the spec names exists here
from the start, even where the Turn cannot emit it yet, so that the reducer, the API and the
later tickets are all written against one shape: `offer` and `handover` are filled in by
ticket 11, and `done.trace_id` stops being null in ticket 06.

`card` was declared by ticket 02 with nothing to emit it; ticket 08 gives it its first real
definition, and `destination` becomes the resolved link rather than a bare id — the browser
cannot look an id up, and nothing else in the app should have to.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from core.handover import HandoverMode
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


@dataclass(frozen=True)
class CardDestination:
    """Where a Walkthrough Card's call to action takes the Visitor.

    Resolved on the server from an id in the destination catalogue (`core/tools/walkthroughs`),
    so the browser renders a link it was given rather than one it worked out, and the Assistant
    can only ever name a destination that exists. `external` splits the two behaviours the
    Visitor can see: a Portal route is a client-side navigation that leaves the chat panel
    mounted, an external link opens in a new tab.
    """

    id: str
    label: str
    href: str
    external: bool


def card_event(
    title: str,
    steps: Sequence[str],
    destination: CardDestination,
    citations: Sequence[str] = (),
) -> ChatEvent:
    """A Walkthrough Card: the steps and the resolved destination."""
    return ChatEvent(
        "card",
        {
            "title": title,
            "steps": list(steps),
            "destination": {
                "id": destination.id,
                "label": destination.label,
                "href": destination.href,
                "external": destination.external,
            },
            "citations": list(citations),
        },
    )


def escalation_event(
    title: str,
    body: str,
    next_step: str,
    citations: Sequence[str] = (),
    language: str | None = None,
) -> ChatEvent:
    """An Escalation: what is known, what cannot be confirmed, one concrete next step.

    `language` is the language the copy was looked up in. It is on the wire because the card's
    own chrome — the "Next step:" label — belongs to the card, not to the widget: a Spanish
    refusal under an English label reads as a bug the Assistant made. It is optional, so an
    Escalation raised without a language still renders under the widget's own toggle.
    """
    payload: dict[str, Any] = {
        "title": title,
        "body": body,
        "next_step": next_step,
        "citations": list(citations),
    }
    if language is not None:
        payload["language"] = language
    return ChatEvent("escalation", payload)


def offer_event(request_id: str, prompt: str) -> ChatEvent:
    """The offer of a Hand-over, made at most once per Session. Ticket 11 emits it."""
    return ChatEvent("offer", {"request_id": request_id, "prompt": prompt})


def handover_event(request_id: str, state: str, mode: HandoverMode | None) -> ChatEvent:
    """A Handover Request changing state. The mode is null until the Visitor accepts, and
    stays null on a declined offer — a Hand-over that never happened has no mode."""
    return ChatEvent("handover", {"request_id": request_id, "state": state, "mode": mode})


def done_event(
    usage: Usage,
    trace_id: str | None = None,
    redactions: Mapping[str, int] | None = None,
) -> ChatEvent:
    """The Turn is complete. `trace_id` stays null until Langfuse arrives in ticket 06.

    `redactions` is the Turn's redaction manifest — `{category: count}`, never a value — and
    the key is present only when something was redacted, so a client written against the
    earlier payload sees exactly the payload it was written against.
    """
    data: dict[str, Any] = {
        "trace_id": trace_id,
        "usage": {
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "cached_tokens": usage.cached_tokens,
            "cost_usd": usage.cost_usd,
        },
    }
    if redactions:
        data["redactions"] = dict(redactions)
    return ChatEvent("done", data)


def error_event(message: str) -> ChatEvent:
    """The Turn failed. The message is written for a Visitor: never a stack trace, never a
    provider's own wording, never an id or a key."""
    return ChatEvent("error", {"message": message})
