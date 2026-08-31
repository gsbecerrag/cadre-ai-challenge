"""`offer_live_handover` — ask a Qualified Lead, once, whether they want a Strategist now.

The interesting part of this tool is when the model can see it. Two facts decide whether an
offer may be made — the Session's Qualification Score and whether an offer has already been
made — and neither is something the Assistant should be asked to remember. A prompt that said
"only offer above three signals, and only once" would be a rule that can be argued with, drifts
with the wording, and cannot be tested; a tool that is absent from the request cannot be called
at all. So the exposure rule lives here, next to the tool, as an availability predicate the
registry filters the definitions with (ADR-0009).

What the tool does when it is called is deliberately small: it creates the Handover Request in
`offered`, tells the Notifier, and streams the `offer` event that becomes the card with Yes and
"Keep chatting". It decides nothing about video or Callback — mode is decided when the Visitor
accepts, from Availability and the flag (ADR-0007), because a Strategist can go offline between
the offer and the answer.
"""

from collections.abc import Mapping
from typing import Any

from core.events import offer_event
from core.handover import HandoverRequest, new_request_id
from core.logging import get_logger
from core.notifier import Notifier
from core.provider import ToolDefinition
from core.store import ConversationStore, lead_snapshot
from core.tools.registry import Tool, ToolOutcome

logger = get_logger("tools.offer_live_handover")

OFFER_TOOL_NAME = "offer_live_handover"

# The longest line that still reads as one question in a chat bubble.
MAX_PROMPT_LENGTH = 160

# What the model reads after the card has been shown. It is told the Visitor is now looking at
# buttons, because the failure mode here is an Assistant that asks the same question again in
# prose and leaves the Visitor with two ways to say yes.
OFFER_SHOWN = (
    "The Visitor is now looking at the offer card with its two buttons, so the offer has been "
    "made. Do not ask again, do not repeat the question in your reply, and do not describe the "
    "card. Say at most one short sentence and let them choose; if they say no, accept it "
    "gracefully and carry on with whatever they ask next."
)

# What the model reads when it reaches for the tool it should no longer have. The registry
# normally keeps it out of reach, so this is the belt to that braces: a model working from a
# cached tool list, or one that invented the name, is answered rather than obeyed.
ALREADY_OFFERED = (
    "This Session has already been offered a Hand-over, so nothing was shown. A Visitor asked "
    "twice is a Visitor being sold to. If they are asking for a person again, point them at "
    "hello@gocadre.ai, (619) 324-3223 or the contact form instead."
)

NOT_QUALIFIED = (
    "No Hand-over was offered: this Session has no Lead with enough Qualification Signals yet. "
    "Keep answering the Visitor's question, and call `capture_lead` with what they tell you "
    "about themselves as it comes up."
)

DEFINITION = ToolDefinition(
    name=OFFER_TOOL_NAME,
    description=(
        "Offer the Visitor a call with a Cadre Strategist, right now. Call it once, when the "
        "Visitor has shown real interest — they asked to speak to someone, or the conversation "
        "has reached the point where a Strategist is the honest next step. It shows a card "
        "with a Yes button and a Keep-chatting button, so ask nothing about it in your own "
        "words: say one short sentence at most and let them press. You will not be given this "
        "tool again once an offer has been made in this Session."
    ),
    parameters={
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": (
                    "One short question to put on the card, in the Visitor's language — for "
                    'example "Do you want to jump into a call with our experts?". Leave it '
                    "out to use Cadre's own wording."
                ),
            }
        },
        "required": [],
        "additionalProperties": False,
    },
)


def offer_live_handover_tool(store: ConversationStore, notifier: Notifier) -> Tool:
    """The tool, bound to the store the Handover Request is written to and the Notifier."""

    async def available(session_id: str) -> bool:
        """Whether the model may be given this tool on this call.

        Asked per provider call rather than once per Turn, so the Turn in which `capture_lead`
        takes a Lead over the threshold is the Turn in which the offer becomes possible — a
        Visitor who introduces themselves and asks for a person in one message should not have
        to ask again.
        """
        lead = await store.get_lead(session_id)
        if lead is None or not lead.qualified:
            return False
        return await store.handover_for_session(session_id) is None

    async def run(arguments: Mapping[str, Any], session_id: str) -> ToolOutcome:
        lead = await store.get_lead(session_id)
        if lead is None or not lead.qualified:
            logger.info("Hand-over offer refused: the Lead is not a Qualified Lead")
            return ToolOutcome(result=NOT_QUALIFIED)
        if await store.handover_for_session(session_id) is not None:
            logger.info("Hand-over offer refused: this Session has already been offered one")
            return ToolOutcome(result=ALREADY_OFFERED)

        prompt = str(arguments.get("prompt") or "").strip()[:MAX_PROMPT_LENGTH]
        request = await store.create_handover(
            HandoverRequest(
                id=new_request_id(),
                session_id=session_id,
                state="offered",
                prompt=prompt,
                lead=lead_snapshot(lead),
            )
        )
        # After the write, so a channel that reacts to this describes a request that exists.
        await notifier.handover_created(request)
        logger.info(
            "Hand-over offered",
            extra={"request_id": request.id, "qualification_score": lead.score},
        )
        return ToolOutcome(result=OFFER_SHOWN, events=(offer_event(request.id, prompt),))

    return Tool(definition=DEFINITION, run=run, available=available)
