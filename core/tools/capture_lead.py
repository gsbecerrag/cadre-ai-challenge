"""`capture_lead` — record what the Visitor has told us about themselves, and score it in code.

The Assistant calls this the moment a Visitor shares any one Contact Detail, and again whenever
another detail or another Qualification Signal turns up. It passes what it learned; it never
passes a score. The score is counted here from the signals (`core.qualification`, ADR-0009),
which is what makes the Hand-over gate in ticket 11 something a Strategist can argue with and a
test can pin, rather than a number a prompt produced.

The merge lives here rather than in the store: read the Session's Lead, fold this call's
Contact Details and signals into it, count the score, write the whole Lead back. An argument
the model leaves out is not an erasure — a later call carrying only a phone number keeps the
email from three Turns ago.
"""

from collections.abc import Mapping
from typing import Any

from core.logging import get_logger
from core.provider import ToolDefinition
from core.qualification import (
    DEFAULT_QUALIFICATION_THRESHOLD,
    MAX_QUALIFICATION_SCORE,
    SIGNAL_NAMES,
    is_qualified,
    present_signals,
    qualification_score,
)
from core.store import CONTACT_DETAIL_NAMES, ConversationStore, Lead
from core.tools.registry import Tool, ToolOutcome

logger = get_logger("tools.capture_lead")

# What the model reads when it called the tool with nothing to reach the Visitor by. A Lead
# with no Contact Detail is not a Lead, so nothing is written — and this comes back as a result
# the model can act on rather than as a failed Turn.
NO_CONTACT_DETAIL = (
    "There is no Lead for this Session yet and this call carries no Contact Detail, so no Lead "
    "was recorded. Call `capture_lead` again once the Visitor has given you at least one of a "
    "name, work email, company, phone number or role — and do not interrogate them for it."
)

_CONTACT_DETAIL_DESCRIPTIONS: Mapping[str, str] = {
    "name": "The Visitor's name, exactly as they gave it.",
    "email": "The Visitor's work email address, exactly as they gave it.",
    "company": "The company the Visitor works for.",
    "phone": "The Visitor's phone number, exactly as they gave it.",
    "role": "The Visitor's job title or role.",
}

_SIGNAL_DESCRIPTIONS: Mapping[str, str] = {
    "industry_fit": (
        "The Visitor's industry, in a few words, when they have named one or it is plain from "
        "what they described."
    ),
    "company_size_or_role": (
        "How big the company is or how senior the Visitor is — headcount, revenue band, or "
        "their seniority — in a few words."
    ),
    "initiative_or_pain": (
        "The concrete initiative they are pursuing or the problem that is costing them, in a "
        "few words. Not a general interest in AI."
    ),
    "timeline_or_budget": (
        "When they want this done, or what they have to spend, in a few words — only when they "
        "volunteered it. Never ask a Visitor for a budget."
    ),
    "explicit_intent": (
        "What they actually asked for, when they have asked to speak to someone, to book a "
        "call, or to start an engagement."
    ),
}

DEFINITION = ToolDefinition(
    name="capture_lead",
    description=(
        "Record the Visitor's Contact Details and what you have learned about their situation, "
        "so that a Strategist can pick the conversation up. Call it as soon as the Visitor "
        "gives you any one Contact Detail — a name, work email, company, phone number or role "
        "— and call it again whenever another detail or another signal appears: the same Lead "
        "is updated and anything you leave out is kept. Pass only what the Visitor actually "
        "told you, in your own short words; omit what you have not learned, never guess, and "
        "never rate or score the Visitor. The Visitor does not see this tool, so acknowledge "
        "their details in your own reply and carry on with their question."
    ),
    parameters={
        "type": "object",
        "properties": {
            **{
                name: {"type": "string", "description": description}
                for name, description in _CONTACT_DETAIL_DESCRIPTIONS.items()
            },
            **{
                name: {"type": "string", "description": description}
                for name, description in _SIGNAL_DESCRIPTIONS.items()
            },
        },
        "required": [],
        "additionalProperties": False,
    },
)


def _text(value: object) -> str:
    """One argument as the Lead holds it: a model may send `null`, a number, or spaces."""
    return str(value if value is not None else "").strip()


def merged_lead(
    existing: Lead | None,
    session_id: str,
    arguments: Mapping[str, Any],
    threshold: int = DEFAULT_QUALIFICATION_THRESHOLD,
) -> Lead:
    """This call folded into the Session's Lead, with the Qualification Score recounted.

    Pure, so the merge rule and the score are one readable function: an argument that is absent
    or blank keeps what the Lead already had, and every Qualification Signal present in the
    result counts once.
    """
    details = {
        name: _text(arguments.get(name)) or (getattr(existing, name, "") if existing else "")
        for name in CONTACT_DETAIL_NAMES
    }
    signals = dict(existing.signals) if existing else {}
    signals.update({name: value for name in SIGNAL_NAMES if (value := _text(arguments.get(name)))})
    score = qualification_score(signals)
    return Lead(
        session_id=session_id,
        signals=signals,
        score=score,
        qualified=is_qualified(score, threshold),
        **details,
    )


def _result(lead: Lead) -> str:
    """What the model reads next. It is told the score so that it knows the Lead landed — the
    Visitor is never told, because a Visitor being scored is not a conversation."""
    present = ", ".join(present_signals(lead.signals)) or "none yet"
    return (
        f"The Lead for this Session was recorded with {lead.score} of {MAX_QUALIFICATION_SCORE} "
        f"Qualification Signals present ({present}). Acknowledge what the Visitor just shared "
        "in one short clause, then carry on with their question. Never mention this tool, the "
        "Lead, or the score to the Visitor, and do not read their details back to them."
    )


def capture_lead_tool(
    store: ConversationStore,
    *,
    qualification_threshold: int = DEFAULT_QUALIFICATION_THRESHOLD,
) -> Tool:
    """The tool, bound to the `ConversationStore` the Lead is written to."""

    async def run(arguments: Mapping[str, Any], session_id: str) -> ToolOutcome:
        existing = await store.get_lead(session_id)
        if existing is None and not any(
            _text(arguments.get(name)) for name in CONTACT_DETAIL_NAMES
        ):
            logger.info("capture_lead called with no Contact Detail; no Lead recorded")
            return ToolOutcome(result=NO_CONTACT_DETAIL)

        lead = await store.upsert_lead(
            session_id, merged_lead(existing, session_id, arguments, qualification_threshold)
        )
        # Counts only: a log line is not a place for a Visitor's name or email (constraint 8).
        logger.info(
            "Lead captured",
            extra={
                "qualification_score": lead.score,
                "qualified": lead.qualified,
                "contact_details": len(lead.contact_details),
            },
        )
        return ToolOutcome(result=_result(lead))

    return Tool(definition=DEFINITION, run=run)
