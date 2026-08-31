"""The script the stub provider runs under `make dev`, so the widget is demonstrable with no key.

These are not the Assistant's answers — the model writes those from the Knowledge Base once
ticket 03 wires OpenRouter. They exist so the streaming, the citation chips and the Escalation
card can be seen and reviewed without spending anything, and every citation in them names a KB
Section that really exists in `knowledge/` (guarded by a test).

The Trap Questions are scripted too. A demo that only shows the Assistant answering well shows
half the product: what it does with a question it cannot answer is the half that decides
whether Cadre could put it in front of a prospect.
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

MATURITY_ANSWER = (
    "The AI Maturity Index scores your company across Cadre's eight-pillar framework, with a "
    "grade in each area and actionable insights on how to improve "
    "[maturity-index#what-the-ai-maturity-index-is]. It is step 2 of the 45-day Intensive, "
    "and the twelve-month roadmap at the end is designed to raise the score "
    "[maturity-index#where-the-index-sits-in-an-engagement]. There is no self-serve quiz: the "
    "only published route to a score is to contact Cadre "
    "[maturity-index#how-to-get-scored]."
)

SECURITY_ANSWER = (
    "Cadre publishes three data-security commitments: black-boxing your data so it is never "
    "used to train other models, stopping employees sharing company secrets on personal LLMs, "
    "and getting the whole team onto secure, compliant tools "
    "[data-security#what-cadre-publishes-about-data-security]. The agents it builds run with "
    "guardrails and human oversight [data-security#guardrails-on-the-agents-cadre-builds]. On "
    "model choice, Cadre is vendor-agnostic and tiers tasks by the model they need — Haiku for "
    "classification and routing, Sonnet for research and synthesis, Opus for complex due "
    "diligence [partners-and-models#matching-the-model-to-the-task]."
)

PORTAL_ANSWER = (
    "The Cadre Portal tracks four things: the AI tools you have activated, the agents you have "
    "deployed, the training your teams have had, and the results those produce "
    "[portal#what-the-portal-tracks]. Cadre's own words for it are “stay aligned, stay "
    "accountable, and scale what works” [portal#what-the-portal-is-for]."
)

CONTACT_NEXT_STEP = (
    "Use the contact form at https://www.cadreai.com/contact, write to hello@gocadre.ai, or "
    "call (619) 324-3223 [contact#how-to-reach-cadre]."
)


def _escalation(
    call_id: str,
    reason: str,
    known: str = "",
    next_step: str = CONTACT_NEXT_STEP,
    language: str = "en",
) -> ToolCall:
    return ToolCall(
        id=call_id,
        name="escalate",
        arguments={
            "reason": reason,
            "known": known,
            "next_step": next_step,
            "language": language,
        },
    )


PRICING_ESCALATION = _escalation(
    "demo-escalate-pricing",
    "pricing",
    known=(
        "What I can tell you is what you would be buying: the 45-day AI Transformation "
        "Intensive takes a company from zero clarity to a prioritised roadmap "
        "[services#the-ai-transformation-intensive]."
    ),
)

PRICING_ESCALATION_ES = _escalation(
    "demo-escalate-pricing-es",
    "pricing",
    known=(
        "Lo que sí puedo decirte es qué incluye: el Intensivo de Transformación con IA de 45 "
        "días lleva a una empresa de cero claridad a una hoja de ruta priorizada "
        "[services#the-ai-transformation-intensive]."
    ),
    next_step=(
        "Escribe a hello@gocadre.ai, llama al (619) 324-3223, o usa el formulario en "
        "https://www.cadreai.com/contact [contact#how-to-reach-cadre]."
    ),
    language="es",
)

PORTAL_LOGIN_ESCALATION = _escalation(
    "demo-escalate-portal",
    "portal_access",
    known=(
        "The Portal itself is real and tracks tools, agents, training and results "
        "[portal#what-the-portal-tracks]."
    ),
    next_step=(
        "Use the link your Cadre contact gave you, or ask for it at hello@gocadre.ai "
        "[portal#how-to-access-the-portal]."
    ),
)

CERTIFICATION_ESCALATION = _escalation(
    "demo-escalate-certification",
    "certification",
    known=(
        "What is published is the three data-security commitments on the AI Engineering page "
        "[data-security#what-cadre-publishes-about-data-security]."
    ),
)

HEADCOUNT_ESCALATION = _escalation(
    "demo-escalate-headcount",
    "headcount",
    known=(
        "The About page names eight leaders and publishes delivery numbers rather than a "
        "headcount [not-published#company-size-founding-and-funding], and those numbers are "
        "100+ high-ROI use cases across 50+ companies "
        "[services#why-companies-bring-in-an-ai-partner]."
    ),
)

COMPETITOR_ESCALATION = _escalation(
    "demo-escalate-competitor",
    "competitor",
    known=(
        "What Cadre says about its own approach is that it acts as an integrated AI team and "
        "only builds custom when there is no faster option [services#what-cadre-does]."
    ),
)

GUARANTEE_ESCALATION = _escalation(
    "demo-escalate-guarantee",
    "guarantee",
    known=(
        "The published results come from eight anonymised case studies "
        "[case-studies#how-cadre-publishes-its-case-studies]: 220 hours a month saved on "
        "supplier automation [case-studies#supplier-automation-manufacturing-logistics], "
        "$420,000 a year on a housing visibility system "
        "[case-studies#ai-powered-housing-visibility-system-hospitality]."
    ),
)

UNKNOWN_ESCALATION = _escalation(
    "demo-escalate-unknown",
    "not_in_knowledge_base",
    next_step="Write to hello@gocadre.ai or call (619) 324-3223 [contact#how-to-reach-cadre].",
)


def _streamed(answer: str) -> list[StubEvent]:
    """Chunk an answer the way a model streams one, so the demo shows text arriving."""
    words = answer.split(" ")
    deltas: list[StubEvent] = [
        TextDelta(" ".join(words[start : start + WORDS_PER_DELTA]) + " ")
        for start in range(0, len(words), WORDS_PER_DELTA)
    ]
    return [*deltas, DEMO_USAGE]


def _after(escalation: ToolCall, closing: str) -> list[StubResponse]:
    """A Turn that escalates and then carries on talking, which is what the prompt asks for:
    an Escalation is not the end of the conversation."""
    return [[escalation], _streamed(closing)]


def demo_scripts() -> dict[str, Sequence[StubResponse]]:
    """Keyed by a phrase in the Visitor's message; the quick replies in the widget hit these.

    The stub matches the longest trigger contained in the message, so a narrower phrase can be
    added without reinterpreting an existing one.
    """
    anything_else = "Anything else I can look up for you?"
    return {
        # Grounded answers.
        "cadre ai do": [_streamed(SERVICES_ANSWER)],
        "services": [_streamed(SERVICES_ANSWER)],
        "industries": [_streamed(INDUSTRIES_ANSWER)],
        "strategist": [_streamed(CONTACT_ANSWER)],
        "contact": [_streamed(CONTACT_ANSWER)],
        "maturity": [_streamed(MATURITY_ANSWER)],
        "security": [_streamed(SECURITY_ANSWER)],
        "results": [_streamed(PORTAL_ANSWER)],
        # Trap Questions.
        "cost": _after(PRICING_ESCALATION, anything_else),
        "price": _after(PRICING_ESCALATION, anything_else),
        "cuesta": _after(PRICING_ESCALATION_ES, "¿Algo más que quieras consultar?"),
        "precio": _after(PRICING_ESCALATION_ES, "¿Algo más que quieras consultar?"),
        "log in": _after(PORTAL_LOGIN_ESCALATION, anything_else),
        "login": _after(PORTAL_LOGIN_ESCALATION, anything_else),
        "portal url": _after(PORTAL_LOGIN_ESCALATION, anything_else),
        "soc 2": _after(CERTIFICATION_ESCALATION, anything_else),
        "iso 27001": _after(CERTIFICATION_ESCALATION, anything_else),
        "dpa": _after(CERTIFICATION_ESCALATION, anything_else),
        "how many people": _after(HEADCOUNT_ESCALATION, anything_else),
        "employees": _after(HEADCOUNT_ESCALATION, anything_else),
        "compare": _after(COMPETITOR_ESCALATION, anything_else),
        "better than": _after(COMPETITOR_ESCALATION, anything_else),
        "guarantee": _after(GUARANTEE_ESCALATION, anything_else),
    }


def demo_fallback() -> Sequence[StubResponse]:
    """Anything unscripted gets an honest Escalation rather than an invented answer."""
    return _after(UNKNOWN_ESCALATION, "Is there anything else I can look up for you?")
