"""`show_walkthrough` — answer a "how do I …" question with steps and one link, not prose.

A Visitor asking where their agents' results live wants a route, and a paragraph describing a
route is the worst way to give one: they have to hold it in their head while they go looking.
So the Assistant writes the title and two to four steps, names one destination from the
catalogue, and the chat renders a Walkthrough Card whose call to action goes there.

The split matches `escalate`: the model writes the words, the code owns the link. Every way the
model can get this wrong — a destination that does not exist, one step, nine steps, an empty
title — comes back to it as a tool result it can correct rather than reaching the Visitor
(ADR-0004).
"""

from collections.abc import Mapping, Sequence
from typing import Any

from core.citations import split_citations
from core.events import card_event
from core.provider import ToolDefinition
from core.tools.registry import Tool, ToolOutcome
from core.tools.walkthroughs import DESTINATION_IDS, resolve_destination

MIN_STEPS = 2
MAX_STEPS = 4

DEFINITION = ToolDefinition(
    name="show_walkthrough",
    description=(
        "Show the Visitor a Walkthrough Card: a title, two to four steps, and one link to "
        "where the task is actually done. Use it instead of prose whenever you are describing "
        "how to get somewhere or how a process starts, and a `destination` below matches. "
        "You write the title and the steps; the link comes from the destination id, so never "
        "write a URL into a step."
    ),
    parameters={
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": (
                    "What the Visitor will have done at the end, in their language — "
                    '"See your agents\' results in the Portal".'
                ),
            },
            "steps": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": MIN_STEPS,
                "maxItems": MAX_STEPS,
                "description": (
                    "Two to four steps, one action each, in order, in the Visitor's language. "
                    "Add `[topic#heading]` markers where a step states something the Knowledge "
                    "Base carries."
                ),
            },
            "destination": {
                "type": "string",
                "enum": list(DESTINATION_IDS),
                "description": (
                    "Where the card's button goes. `portal.dashboard`, `portal.tools`, "
                    "`portal.agents` and `portal.training` open the Portal on the page that "
                    "shows that thing; `contact.form` and `maturity.get-scored` open Cadre's "
                    "published contact form, which is where anything that starts with a "
                    "strategist begins. Nothing else is a destination — never invent one."
                ),
            },
        },
        "required": ["title", "steps", "destination"],
        "additionalProperties": False,
    },
)


def _steps(value: object) -> list[str]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise ValueError(
            f"`steps` must be a list of {MIN_STEPS} to {MAX_STEPS} strings, one action each"
        )
    if not all(isinstance(step, str) for step in value):
        # Coercing would satisfy every check below and show the Visitor a card whose steps
        # read "1" and "2" — validated, rendered, and useless.
        raise ValueError("every step is text the Visitor can act on, not a number or an object")
    steps = [step.strip() for step in value if isinstance(step, str)]
    if not all(steps):
        raise ValueError("every step needs text the Visitor can act on")
    if not MIN_STEPS <= len(steps) <= MAX_STEPS:
        raise ValueError(
            f"a Walkthrough Card has {MIN_STEPS} to {MAX_STEPS} steps, not {len(steps)}"
        )
    return steps


def run_show_walkthrough(arguments: Mapping[str, Any]) -> ToolOutcome:
    destination_id = str(arguments.get("destination") or "")
    destination = resolve_destination(destination_id)
    if destination is None:
        # The one failure worth spelling out: the model gets the list back, so its next
        # attempt picks a destination that exists instead of writing a URL of its own.
        raise ValueError(
            f"there is no walkthrough destination {destination_id!r}. The destinations are: "
            f"{', '.join(DESTINATION_IDS)}"
        )

    title, title_citations = split_citations(str(arguments.get("title") or ""))
    if not title:
        raise ValueError("a Walkthrough Card needs a title naming what the Visitor will have done")

    citations = list(title_citations)
    steps: list[str] = []
    for raw_step in _steps(arguments.get("steps")):
        step, step_citations = split_citations(raw_step)
        if not step:
            raise ValueError("every step needs text the Visitor can act on")
        steps.append(step)
        citations.extend(step_citations)

    return ToolOutcome(
        result=(
            f"The Walkthrough Card {title!r} was shown to the Visitor with its {len(steps)} "
            f"steps and a button to {destination.href}. Do not repeat the steps or the link "
            f"in prose."
        ),
        events=(
            card_event(
                title=title,
                steps=steps,
                destination=destination,
                citations=tuple(dict.fromkeys(citations)),
            ),
        ),
    )


SHOW_WALKTHROUGH_TOOL = Tool(definition=DEFINITION, run=run_show_walkthrough)
