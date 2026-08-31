"""`escalate` — redirect the Visitor to a human channel without a human joining the Session.

The Assistant calls this when the Knowledge Base does not answer the question. Ticket 04 writes
the prompt rules and the Trap Question list that decide *when*; this is the mechanism.
"""

from collections.abc import Mapping
from typing import Any

from core.citations import split_citations
from core.events import escalation_event
from core.provider import ToolDefinition
from core.tools.registry import Tool, ToolOutcome

# Ticket 04 replaces this with copy per Escalation reason; today one honest line covers them.
ESCALATION_TITLE = "I can't confirm that from what Cadre publishes"

DEFINITION = ToolDefinition(
    name="escalate",
    description=(
        "Redirect the Visitor to a human channel when the Knowledge Base does not answer "
        "their question. Say what you do know and what you cannot confirm in `reason`, and "
        "give exactly one concrete next step in `next_step`."
    ),
    parameters={
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "description": "What is known and what cannot be confirmed, for the Visitor.",
            },
            "next_step": {
                "type": "string",
                "description": "One concrete next step: the contact form, the email, or the "
                "published phone number.",
            },
        },
        "required": ["reason", "next_step"],
        "additionalProperties": False,
    },
)


def run_escalate(arguments: Mapping[str, Any]) -> ToolOutcome:
    reason, reason_citations = split_citations(str(arguments["reason"]))
    next_step, next_step_citations = split_citations(str(arguments["next_step"]))
    if not reason or not next_step:
        raise ValueError("an Escalation needs both a reason and a next step")
    return ToolOutcome(
        result="The Escalation was shown to the Visitor. Do not repeat the next step in prose.",
        events=(
            escalation_event(
                title=ESCALATION_TITLE,
                body=reason,
                next_step=next_step,
                citations=tuple(dict.fromkeys(reason_citations + next_step_citations)),
            ),
        ),
    )


ESCALATE_TOOL = Tool(definition=DEFINITION, run=run_escalate)
