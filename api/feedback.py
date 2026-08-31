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
- **One Feedback per Trace, changed once.** A second thumb corrects a misclick; a third is a
  control being held down, and it is refused with a conflict. So the Triage Agent sees one
  rating per Turn rather than a stream of them, and one thumb cannot become a write loop.
- **The comment goes through the `full` Redaction Profile.** It is a free-text box, so a
  Visitor will type their email into it, and what is written here is read by the Triage Agent
  and copied to an observability vendor (ADR-0006).
"""

from collections.abc import Mapping

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

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
    and whether this request changed an earlier one — because after a change there is no
    further change to offer."""

    feedback_id: str
    rating: Rating
    changed: bool


def create_feedback_router(
    store: ConversationStore, *, tracer: Tracer, cookie_secret: str
) -> APIRouter:
    """The Feedback route, with the store, the tracer and the cookie's key closed over."""
    router = APIRouter(tags=["feedback"])

    @router.post("/feedback")
    async def leave_feedback(request: Request, submission: FeedbackRequest) -> FeedbackReceipt:
        session_id = read_session_id(request, cookie_secret)
        # No Session at all and a Trace from someone else's are the same answer on purpose: a
        # caller with no conversation has nothing to rate, and minting them a fresh Session —
        # which every other endpoint does — would be issuing a cookie to say "not found".
        if session_id is None or not await store.trace_belongs_to(session_id, submission.trace_id):
            logger.info("Feedback refused for a Trace outside the Session")
            raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_THIS_SESSIONS_TRACE)

        with session_context(session_id):
            existing = await store.get_feedback(session_id, submission.trace_id)
            if existing is not None and existing.changes >= MAX_FEEDBACK_CHANGES:
                raise HTTPException(status.HTTP_409_CONFLICT, ALREADY_CHANGED)

            stored = await store.save_feedback(
                Feedback(
                    session_id=session_id,
                    trace_id=submission.trace_id,
                    rating=submission.rating,
                    comment=redaction.full(submission.comment).text,
                    changes=0 if existing is None else existing.changes + 1,
                )
            )
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
            return FeedbackReceipt(
                feedback_id=stored.id, rating=stored.rating, changed=stored.changed
            )

    return router
