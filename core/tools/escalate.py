"""`escalate` — redirect the Visitor to a human channel without a human joining the Session.

The Assistant calls this when the Knowledge Base does not answer the question. It chooses the
*reason* and writes what it does know and one concrete next step; it never writes the title or
the refusal itself. Those come from the table below, verbatim from the design artboard
(docs/design/DESIGN-BRIEF.md §2.5) in both languages.

That split is the point of the tool. A refusal composed by the model is a refusal that can
drift — into a hedge, into an apology, or into the very number it is refusing to give. A
refusal looked up by reason reads the same every time, says only what Cadre has actually
published about the absence, and cites the KB Section that records it.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from core.citations import split_citations
from core.events import escalation_event
from core.provider import ToolDefinition
from core.tools.registry import Tool, ToolOutcome

Language = Literal["en", "es"]

EscalationReason = Literal[
    "pricing",
    "portal_access",
    "certification",
    "headcount",
    "availability",
    "competitor",
    "guarantee",
    "not_in_knowledge_base",
    "other",
]

ESCALATION_REASONS: tuple[EscalationReason, ...] = (
    "pricing",
    "portal_access",
    "certification",
    "headcount",
    "availability",
    "competitor",
    "guarantee",
    "not_in_knowledge_base",
    "other",
)

LANGUAGES: tuple[Language, ...] = ("en", "es")
DEFAULT_LANGUAGE: Language = "en"

# A model can put anything in an enum field. An unrecognised reason is still an Escalation, so
# it reads as the honest generic one rather than ending the Visitor's Turn.
FALLBACK_REASON: EscalationReason = "not_in_knowledge_base"


@dataclass(frozen=True)
class EscalationCopy:
    """The fixed half of an Escalation card: what Cadre says about this kind of absence."""

    title: str
    body: str


_GENERIC: Mapping[Language, EscalationCopy] = {
    "en": EscalationCopy(
        title="I don't have that information",
        body=(
            "I don't have that information in what Cadre publishes, so I won't guess. "
            "[not-published#anything-not-listed-here]"
        ),
    ),
    "es": EscalationCopy(
        title="No tengo esa información",
        body=(
            "No tengo esa información en lo que Cadre publica, así que no voy a adivinar. "
            "[not-published#anything-not-listed-here]"
        ),
    ),
}

ESCALATION_COPY: Mapping[EscalationReason, Mapping[Language, EscalationCopy]] = {
    "pricing": {
        "en": EscalationCopy(
            title="Cadre doesn't publish pricing",
            body=(
                "I can't quote a price for Strategy, Facilitation, Engineering, or Agents "
                "engagements — Cadre doesn't publish them. The only published price is the "
                "PE AI Value Creation Playbook at $5,000 per firm. [not-published#pricing]"
            ),
        ),
        "es": EscalationCopy(
            title="Cadre no publica precios",
            body=(
                "No puedo cotizar Estrategia, Facilitación, Ingeniería ni Agentes — Cadre no "
                "publica esos precios. El único precio publicado es el PE AI Value Creation "
                "Playbook: $5,000 por firma. [not-published#pricing]"
            ),
        ),
    },
    "portal_access": {
        "en": EscalationCopy(
            title="Cadre doesn't publish a Portal login",
            body=(
                "The Cadre Portal tracks tools, agents, training and results, but there is no "
                "published login page or portal address anywhere on cadreai.com, so I can't "
                "send you one. [not-published#portal-login]"
            ),
        ),
        "es": EscalationCopy(
            title="Cadre no publica un acceso al Portal",
            body=(
                "El Portal de Cadre registra herramientas, agentes, capacitación y resultados, "
                "pero no hay ninguna página de acceso ni dirección publicada en cadreai.com, "
                "así que no puedo darte una. [not-published#portal-login]"
            ),
        ),
    },
    "certification": {
        "en": EscalationCopy(
            title="I can't confirm a certification Cadre hasn't published",
            body=(
                "Cadre publishes no SOC 2 report, ISO 27001 certification, data-processing "
                "agreement, encryption detail or data-residency commitment — only three "
                "data-security statements and the policies for its own website. I won't tell "
                "you it holds one. [not-published#security-certifications-and-data-agreements]"
            ),
        ),
        "es": EscalationCopy(
            title="No puedo confirmar una certificación que Cadre no publica",
            body=(
                "Cadre no publica ningún informe SOC 2, certificación ISO 27001, acuerdo de "
                "tratamiento de datos, detalle de cifrado ni compromiso de residencia de "
                "datos — solo tres declaraciones de seguridad y las políticas de su propio "
                "sitio. No voy a afirmar que la tiene. "
                "[not-published#security-certifications-and-data-agreements]"
            ),
        ),
    },
    "headcount": {
        "en": EscalationCopy(
            title="Cadre doesn't publish those company details",
            body=(
                "Cadre publishes no headcount, founding year or funding history, so I have no "
                "number to give you. [not-published#company-size-founding-and-funding]"
            ),
        ),
        "es": EscalationCopy(
            title="Cadre no publica esos datos de la empresa",
            body=(
                "Cadre no publica el número de empleados, el año de fundación ni su "
                "financiamiento, así que no tengo una cifra que darte. "
                "[not-published#company-size-founding-and-funding]"
            ),
        ),
    },
    "availability": {
        "en": EscalationCopy(
            title="I can't promise you a particular person or date",
            body=(
                "Cadre publishes its leadership team but never who is available or when an "
                "engagement could start, so I can't commit anyone by name. "
                "[not-published#named-availability-and-start-dates]"
            ),
        ),
        "es": EscalationCopy(
            title="No puedo comprometer a una persona ni una fecha",
            body=(
                "Cadre publica su equipo de liderazgo pero nunca quién está disponible ni "
                "cuándo podría empezar un proyecto, así que no puedo comprometer a nadie por "
                "su nombre. [not-published#named-availability-and-start-dates]"
            ),
        ),
    },
    "competitor": {
        "en": EscalationCopy(
            title="I can't compare Cadre with another firm",
            body=(
                "Cadre publishes nothing about other consultancies, and I answer only from "
                "what Cadre publishes — any comparison I gave you would be invented. "
                "[not-published#comparisons-with-other-firms]"
            ),
        ),
        "es": EscalationCopy(
            title="No puedo comparar a Cadre con otra firma",
            body=(
                "Cadre no publica nada sobre otras consultoras, y solo respondo con base en lo "
                "que Cadre publica — cualquier comparación que te diera sería inventada. "
                "[not-published#comparisons-with-other-firms]"
            ),
        ),
    },
    "guarantee": {
        "en": EscalationCopy(
            title="I can't promise an outcome",
            body=(
                "Cadre publishes results from past engagements but publishes no guarantee "
                "of outcomes, savings, timelines or refunds, and its terms say the "
                "services are provided as-is. [not-published#outcome-guarantees]"
            ),
        ),
        "es": EscalationCopy(
            title="No puedo prometer un resultado",
            body=(
                "Cadre publica resultados de proyectos anteriores pero no publica ninguna "
                "garantía de resultados, ahorros, plazos ni reembolsos, y sus términos "
                "indican que los servicios se prestan tal cual. "
                "[not-published#outcome-guarantees]"
            ),
        ),
    },
    "not_in_knowledge_base": _GENERIC,
    "other": _GENERIC,
}

DEFINITION = ToolDefinition(
    name="escalate",
    description=(
        "Hand a question to a human when the Knowledge Base does not answer it. Pick the "
        "`reason` that matches; put what you can say from the Knowledge Base in `known`, with "
        "its citation markers, or leave it empty when the Knowledge Base says nothing; give "
        "exactly one concrete next step in `next_step`. The Visitor reads Cadre's own wording "
        "for the refusal — do not write it yourself, and never guess the fact you are "
        "escalating."
    ),
    parameters={
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "enum": list(ESCALATION_REASONS),
                "description": (
                    "Why this cannot be answered: `pricing` for a cost, quote or discount; "
                    "`portal_access` for a Portal address or login; `certification` for SOC 2, "
                    "ISO 27001, a DPA, encryption or data residency; `headcount` for company "
                    "size, founding or funding; `availability` for a named person or a start "
                    "date; `competitor` for a comparison with another firm; `guarantee` for a "
                    "promised outcome or refund; `not_in_knowledge_base` for anything else the "
                    "Knowledge Base does not cover; `other` only when none of these fit."
                ),
            },
            "known": {
                "type": "string",
                "description": (
                    "What you can honestly say from the Knowledge Base about the question, "
                    "with `[topic#heading]` markers. Empty string when there is nothing."
                ),
            },
            "next_step": {
                "type": "string",
                "description": (
                    "One concrete next step: the contact form, the email address, or the "
                    "published phone number."
                ),
            },
            "language": {
                "type": "string",
                "enum": list(LANGUAGES),
                "description": "The language the Visitor is writing in.",
            },
        },
        "required": ["reason", "known", "next_step", "language"],
        "additionalProperties": False,
    },
)


def _reason(value: object) -> EscalationReason:
    for reason in ESCALATION_REASONS:
        if value == reason:
            return reason
    return FALLBACK_REASON


def _language(value: object) -> Language:
    for language in LANGUAGES:
        if value == language:
            return language
    return DEFAULT_LANGUAGE


async def run_escalate(arguments: Mapping[str, Any], session_id: str = "") -> ToolOutcome:
    """`session_id` is unused: an Escalation is shown to the Visitor and stored as part of the
    Turn, and writes nothing of its own. Every tool takes the same two arguments."""
    reason = _reason(arguments.get("reason"))
    language = _language(arguments.get("language"))
    copy = ESCALATION_COPY[reason][language]

    known = str(arguments.get("known") or "").strip()
    # The refusal first, then what the Assistant can stand behind: the Visitor should read why
    # there is no answer before reading the part that is nearly one.
    body, body_citations = split_citations(f"{copy.body} {known}" if known else copy.body)
    next_step, next_step_citations = split_citations(str(arguments.get("next_step") or ""))
    if not next_step:
        # An Escalation with nothing for the Visitor to do is worse than none at all, so this
        # goes back to the model as a result it can correct rather than to the browser.
        raise ValueError("an Escalation needs one concrete next step for the Visitor")

    return ToolOutcome(
        result=(
            f"The Escalation for {reason!r} was shown to the Visitor in Cadre's published "
            f"wording ({language}). Do not repeat the next step or the refusal in prose."
        ),
        events=(
            escalation_event(
                title=copy.title,
                body=body,
                next_step=next_step,
                citations=tuple(dict.fromkeys(body_citations + next_step_citations)),
                language=language,
            ),
        ),
    )


ESCALATE_TOOL = Tool(definition=DEFINITION, run=run_escalate)
