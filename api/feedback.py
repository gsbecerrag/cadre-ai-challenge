"""`POST /api/feedback` — a Visitor's thumb on the Turn they have just read.

The one endpoint a Visitor reaches that is not a Turn, and the smallest one in the service: it
writes a Feedback document and mirrors it to Langfuse as a score on the Trace of the Turn it
judges. Both halves matter and they answer different questions — the document is the event
source the Triage Agent runs on (ADR-0005), the score is what makes "the Turns Visitors
disliked" one filter next to the cost and the tokens of the same Turn.

Three rules make up the whole contract:

- **A Trace is rated by the Session that produced it.** A Trace id is not a capability: it
  travels to one browser in one `done` event, and a Session that did not produce it gets a 404
  — not a 403, because "that one is not yours" tells a caller a Trace they guessed exists.
- **One Feedback per Trace, changed once.** The *other* thumb corrects a misclick; a second
  correction is a control being held down, and it is refused with a conflict. The **same**
  thumb again is not a change at all: the widget sends the rating the moment it is pressed and
  the Visitor's sentence a moment later, so one opinion arrives as two requests, and a repeat
  is an idempotent update of the Feedback that stands. So the Triage Agent sees one rating per
  Turn rather than a stream of them, and a double-click costs the Visitor nothing.
- **The comment goes through the `full` Redaction Profile.** It is a free-text box, so a
  Visitor will type their email into it, and what is written here is read by the Triage Agent
  and copied to an observability vendor (ADR-0006).
"""

from collections.abc import Mapping

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from api.access import AccessGate
from api.session import read_session_id
from core import redaction
from core.logging import get_logger, session_context
from core.store import MAX_FEEDBACK_CHANGES, ConversationStore, Feedback, Rating
from core.tracing import FEEDBACK_SCORE_NAME, Tracer

# One line, not an incident report: the box under the thumbs is for "it answered the wrong
# question", and anything longer belongs in a conversation with a Strategist.
MAX_COMMENT_LENGTH = 500

# The shape of an id this service issues — the Session cookie's alphabet, which is also every
# character a Langfuse Trace id can contain. Enforced rather than assumed because the id is
# used as a Firestore document id, and a `/` in one is a path into a collection nobody meant
# to write to.
TRACE_ID_PATTERN = r"^[A-Za-z0-9_-]{1,128}$"

# 1 for a thumbs-up and 0 for a thumbs-down, so the average of the score is the share of Turns
# Visitors liked — the number a dashboard wants, from the same field a filter reads.
SCORE_VALUES: Mapping[Rating, float] = {"up": 1.0, "down": 0.0}

NOT_THIS_SESSIONS_TRACE = "There is no answer with that id in this conversation."
ALREADY_CHANGED = "This answer has already been rated, and the rating has been changed once."

logger = get_logger("api.feedback")


class FeedbackRequest(BaseModel):
    """What the thumbs post: which answer, which way, and optionally why."""

    trace_id: str = Field(pattern=TRACE_ID_PATTERN)
    rating: Rating
    comment: str = Field(default="", max_length=MAX_COMMENT_LENGTH)


class FeedbackReceipt(BaseModel):
    """What the widget locks its control on: the Feedback's id, the rating that now stands,
    and whether the Visitor has spent their one change — because after that there is no
    further change to offer. `changed` describes the Feedback, not this request, so a note
    added to a rating that was already changed still reads as changed."""

    feedback_id: str
    rating: Rating
    changed: bool


def receipt(feedback: Feedback) -> FeedbackReceipt:
    return FeedbackReceipt(
        feedback_id=feedback.id, rating=feedback.rating, changed=feedback.changed
    )


def comment_for(existing: Feedback | None, submission: FeedbackRequest, changed_mind: bool) -> str:
    """The sentence the Feedback ends up carrying, through the `full` Redaction Profile.

    An empty comment means "nothing to add", never "delete what I wrote": the widget sends the
    rating on the press and the note afterwards, so most requests arrive with no comment at
    all. The one exception is a change of mind — the sentence explained the thumb it came with,
    and keeping "exactly what I needed" under a thumbs-down would misreport the Visitor.
    """
    if submission.comment:
        return redaction.full(submission.comment).text
    return existing.comment if existing is not None and not changed_mind else ""


def create_feedback_router(
    store: ConversationStore, *, gate: AccessGate, tracer: Tracer, cookie_secret: str
) -> APIRouter:
    """The Feedback route, with the store, the tracer and the cookie's key closed over."""
    router = APIRouter(tags=["feedback"])

    @router.post("/feedback")
    async def leave_feedback(request: Request, submission: FeedbackRequest) -> FeedbackReceipt:
        # A thumbs-down runs the Triage Agent, which spends the model key too.
        gate.check(request)
        session_id = read_session_id(request, cookie_secret)
        # No Session at all and a Trace from someone else's are the same answer on purpose: a
        # caller with no conversation has nothing to rate, and minting them a fresh Session —
        # which every other endpoint does — would be issuing a cookie to say "not found".
        if session_id is None:
            logger.info("Feedback refused for a caller with no Session")
            raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_THIS_SESSIONS_TRACE)

        with session_context(session_id):
            if not await store.trace_belongs_to(session_id, submission.trace_id):
                logger.info("Feedback refused for a Trace outside the Session")
                raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_THIS_SESSIONS_TRACE)

            existing = await store.get_feedback(session_id, submission.trace_id)
            changed_mind = existing is not None and existing.rating != submission.rating
            if existing is not None and changed_mind and existing.changes >= MAX_FEEDBACK_CHANGES:
                raise HTTPException(status.HTTP_409_CONFLICT, ALREADY_CHANGED)

            feedback = Feedback(
                session_id=session_id,
                trace_id=submission.trace_id,
                rating=submission.rating,
                comment=comment_for(existing, submission, changed_mind),
                # Only the other thumb spends the change. Pressing the same one again is the
                # widget sending the note that goes with a rating it has already sent.
                changes=(existing.changes + (1 if changed_mind else 0)) if existing else 0,
            )
            if existing is not None and existing == feedback:
                # A double-click, a retried request, a second tab agreeing with the first.
                # Nothing about the Feedback has changed, so nothing is written and nothing is
                # said about it — a repeated score would otherwise be a second row in Langfuse
                # and a second document event for the Triage Agent.
                return receipt(existing)

            stored = await store.save_feedback(feedback)
            # After the write, never before it: the document is what the Triage Agent runs on,
            # and a score in Langfuse for a thumb that was never stored is a Turn flagged with
            # nothing behind it. The tracing boundary swallows whatever Langfuse says.
            tracer.score(
                trace_id=stored.trace_id,
                name=FEEDBACK_SCORE_NAME,
                value=SCORE_VALUES[stored.rating],
                comment=stored.comment,
            )
            logger.info(
                "Feedback recorded", extra={"rating": stored.rating, "changed": stored.changed}
            )
            return receipt(stored)

    return router
