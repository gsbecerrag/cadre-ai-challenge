"""The script the stub provider runs under `make dev`, so the widget is demonstrable with no key.

These are not the Assistant's answers — the model writes those from the Knowledge Base once
ticket 03 wires OpenRouter. They exist so the streaming, the citation chips and the Escalation
card can be seen and reviewed without spending anything, and every citation in them names a KB
Section that really exists in `knowledge/`.
"""

from collections.abc import Sequence

from core.adapters.stub_provider import StubEvent, StubResponse
from core.provider import TextDelta, ToolCall, Usage

WORDS_PER_DELTA = 5

# Plausible for a ~13K-token cached prompt on Sonnet 5 (docs/research/openrouter-facts.md).
DEMO_USAGE = Usage(input_tokens=13_100, output_tokens=96, cached_tokens=12_800, cost_usd=0.0042)

SERVICES_ANSWER = (
    "Cadre AI is a consultancy focused on using AI to drive real revenue growth and improve "
    "EBITDA [services#what-cadre-does]. There are four core services: AI Strategy, AI "
    "Leadership & Facilitation, AI Engineering, and AI Agents [services#what-cadre-does]. "
    "AI Strategy runs as the 45-day AI Transformation Intensive, which takes a company from "
    "zero clarity to a prioritised roadmap [services#ai-strategy]."
)

INDUSTRIES_ANSWER = (
    "Cadre publishes nine industries: Professional Services, Private Equity, Real Estate, "
    "Financial Services, Mortgage & Lending, Construction, Retail & E-commerce, Manufacturing "
    "& Logistics, and Hospitality [industries#industries-cadre-serves]. The best fit is a "
    "business with manual workflows that get less efficient as it grows "
    "[industries#best-fit-companies]."
)

CONTACT_ANSWER = (
    "There is no booking calendar on cadreai.com — every “talk to an AI strategist” "
    "call to action goes to the contact form [contact#booking-a-call-with-an-ai-strategist]. "
    "You can use the form at https://www.cadreai.com/contact, write to hello@gocadre.ai, or "
    "call (619) 324-3223 [contact#how-to-reach-cadre]."
)

PRICING_ESCALATION = ToolCall(
    id="demo-escalate",
    name="escalate",
    arguments={
        "reason": (
            "Cadre does not publish pricing for its Strategy, Facilitation, Engineering or "
            "Agents engagements, so I can't quote you a figure."
        ),
        "next_step": (
            "Use the contact form at https://www.cadreai.com/contact, write to "
            "hello@gocadre.ai, or call (619) 324-3223 [contact#how-to-reach-cadre]."
        ),
    },
)

UNKNOWN_ESCALATION = ToolCall(
    id="demo-escalate-unknown",
    name="escalate",
    arguments={
        "reason": (
            "I don't have that in what Cadre publishes, and I would rather say so than guess."
        ),
        "next_step": (
            "Write to hello@gocadre.ai or call (619) 324-3223 [contact#how-to-reach-cadre]."
        ),
    },
)


def _streamed(answer: str) -> list[StubEvent]:
    """Chunk an answer the way a model streams one, so the demo shows text arriving."""
    words = answer.split(" ")
    deltas: list[StubEvent] = [
        TextDelta(" ".join(words[start : start + WORDS_PER_DELTA]) + " ")
        for start in range(0, len(words), WORDS_PER_DELTA)
    ]
    return [*deltas, DEMO_USAGE]


def demo_scripts() -> dict[str, Sequence[StubResponse]]:
    """Keyed by a phrase in the Visitor's message; the quick replies in the widget hit these."""
    return {
        "cadre ai do": [_streamed(SERVICES_ANSWER)],
        "services": [_streamed(SERVICES_ANSWER)],
        "industries": [_streamed(INDUSTRIES_ANSWER)],
        "cost": [[PRICING_ESCALATION], _streamed("Happy to help with anything else.")],
        "price": [[PRICING_ESCALATION], _streamed("Happy to help with anything else.")],
        "strategist": [_streamed(CONTACT_ANSWER)],
        "contact": [_streamed(CONTACT_ANSWER)],
    }


def demo_fallback() -> Sequence[StubResponse]:
    """Anything unscripted gets an honest Escalation rather than an invented answer."""
    return [[UNKNOWN_ESCALATION], _streamed("Is there anything else I can look up for you?")]
