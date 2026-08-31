"""The Visitor's side of the Hand-over: accept, decline, share details, and who is online.

Three things a browser with a Session cookie may do, and one thing anybody may ask.

The Session cookie is the whole authorisation model here (ADR-0010 gives Visitors no account,
and none is wanted): a Handover Request belongs to exactly one Session, so a request that
belongs to another Session is *not found* rather than forbidden — an id in a URL should not be
able to confirm that somebody else's Hand-over exists.

Every transition is validated server-side against the state machine in `core.handover`
(ADR-0007). The browser is not trusted with the rules: a double-clicked button, a retried
request or a hand-written `curl` all reach the same door, and the second accept is a 409.
"""

import re
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field, model_validator

from api.session import read_session_id
from core.handover import (
    DEFAULT_JOIN_TIMEOUT_SECONDS,
    HandoverMode,
    HandoverRequest,
    HandoverState,
    InvalidTransitionError,
    join_timed_out,
    transition,
)
from core.logging import get_logger
from core.qualification import DEFAULT_QUALIFICATION_THRESHOLD
from core.store import ConversationStore, lead_snapshot
from core.tools.capture_lead import merged_lead
from core.video import NoVideoRooms, Room, VideoRoomError, VideoRooms

# Long enough for a real name, a real company and a real work email; short enough that the
# field is not a place to paste a document into.
MAX_DETAIL_LENGTH = 200

NO_SUCH_REQUEST = (
    "That Hand-over is not part of this conversation. If you were offered a call and the "
    "button no longer works, write hello@gocadre.ai or call (619) 324-3223."
)

NO_SESSION = (
    "There is no conversation to attach those details to. Send the Assistant a message first, "
    "or write to hello@gocadre.ai."
)

# Deliberately loose: a local part, an @, a domain with a dot in it, and no whitespace. The
# only thing worth refusing is an address nobody could ever reply to — a Callback with a broken
# address is one a Strategist discovers a day later — and a stricter pattern would start
# refusing real addresses, which is the worse failure of the two.
EMAIL = re.compile(r"^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$")

NOT_AN_EMAIL = "That does not look like an email address a strategist could reply to."

logger = get_logger("api.handover")


class ContactDetails(BaseModel):
    """What the "Your details" card sends: the three fields it draws, and nothing else.

    Not the Qualification Signals: those are what the *Assistant* learned in conversation, and
    a form the Visitor fills in is not a place to raise their own score (ADR-0009).
    """

    name: str = Field(default="", max_length=MAX_DETAIL_LENGTH)
    email: str = Field(default="", max_length=MAX_DETAIL_LENGTH)
    company: str = Field(default="", max_length=MAX_DETAIL_LENGTH)

    @model_validator(mode="after")
    def at_least_one_detail(self) -> "ContactDetails":
        if not any(value.strip() for value in (self.name, self.email, self.company)):
            raise ValueError("Give at least one of a name, a work email or a company.")
        # An empty box is fine — the field is optional, and a Visitor may give only a name.
        # What is refused is something typed into the email box that is not an address.
        if self.email.strip() and not EMAIL.match(self.email.strip()):
            raise ValueError(NOT_AN_EMAIL)
        return self


class LeadContact(BaseModel):
    """The Contact Details the Callback confirmation card reads back to the Visitor.

    Their own, returned to the Session that gave them: nothing here crosses a Session, and the
    card exists so that a Visitor can see what a Strategist will use to reach them.
    """

    name: str
    email: str
    company: str


class HandoverStatus(BaseModel):
    """What the widget needs after a Visitor presses Yes or "Keep chatting" — and every five
    seconds afterwards, while a video Hand-over waits for a Strategist.

    One shape for the answer to a button and the answer to a poll, because they are the same
    question: what is this Hand-over doing now. `room_url` is the Daily room the panel opens
    in an iframe and `strategist_name` is the person the panel names once they have joined;
    both are absent until there is something true to say.
    """

    request_id: str
    state: HandoverState
    mode: HandoverMode | None
    lead: LeadContact
    room_url: str | None = None
    strategist_name: str | None = None


class CapturedLead(BaseModel):
    """What the details card gets back: the Lead as stored, and the score counted in code."""

    lead: LeadContact
    score: int
    qualified: bool


class PublicAvailability(BaseModel):
    """Availability as the chat header may know it: one boolean about the team, no names."""

    any_online: bool


def contact_of(request: HandoverRequest) -> LeadContact:
    return LeadContact(
        name=request.lead.name, email=request.lead.email, company=request.lead.company
    )


def status_of(request: HandoverRequest) -> HandoverStatus:
    """One Handover Request as its own Visitor may read it.

    The Lead is the Visitor's own Contact Details, returned to the Session that gave them, and
    the empty strings become `null` so the widget can ask "is there a room yet" rather than
    "is the room the empty string".
    """
    return HandoverStatus(
        request_id=request.id,
        state=request.state,
        mode=request.mode,
        lead=contact_of(request),
        room_url=request.room_url or None,
        strategist_name=request.strategist_name or None,
    )


def now() -> datetime:
    """The clock the join timeout is measured against. A module function so a test can move
    time forward without the application having to carry a clock it never otherwise needs."""
    return datetime.now(tz=UTC)


def validated(
    stored: HandoverRequest, target: HandoverState, mode: HandoverMode | None = None
) -> HandoverRequest:
    """The request as it would be after this move, or 409.

    Pure: nothing is written until the caller has validated every hop it means to make. Shared
    with the Console (api/console.py), because the Visitor's browser and a Strategist's browser
    reach the same state machine and a second copy of this refusal would be a second answer.
    """
    try:
        return transition(stored, target, mode)
    except InvalidTransitionError as refused:
        logger.info("Handover transition refused", extra={"request_id": stored.id})
        raise HTTPException(status.HTTP_409_CONFLICT, str(refused)) from None


def create_handover_router(
    store: ConversationStore,
    *,
    cookie_secret: str,
    live_handover_enabled: bool,
    video_rooms: VideoRooms | None = None,
    qualification_threshold: int = DEFAULT_QUALIFICATION_THRESHOLD,
    join_timeout_seconds: int = DEFAULT_JOIN_TIMEOUT_SECONDS,
) -> APIRouter:
    """The Visitor's Hand-over routes, with the cookie secret and the configuration closed over.

    All three are passed in rather than read from settings here, so the composition root stays
    the only place that reads configuration and a test can build either deployment. The
    threshold in particular has to be the same number `capture_lead` scores against: `qualified`
    is what unlocks the Hand-over offer, and two paths to one Lead that disagree about it would
    make the offer depend on which of them wrote last.
    """

    router = APIRouter(tags=["handover"])
    rooms = video_rooms if video_rooms is not None else NoVideoRooms()

    async def owned_request(request: Request, request_id: str) -> HandoverRequest:
        """The Handover Request this Session owns, or 404.

        One function for "no cookie", "no such request" and "somebody else's request", because
        they are one answer: this conversation has no such Hand-over.
        """
        session_id = read_session_id(request, cookie_secret)
        stored = await store.get_handover(request_id) if session_id else None
        if stored is None or stored.session_id != session_id:
            logger.info("Handover Request not found for this Session")
            raise HTTPException(status.HTTP_404_NOT_FOUND, NO_SUCH_REQUEST)
        return stored

    async def opened_room(request_id: str) -> Room | None:
        """The Daily room this Hand-over will be held in, or `None` if it could not be opened.

        A failure is not an error the Visitor sees. Lead capture is the thing that must never
        break (the spec, and the whole reason `LIVE_HANDOVER_ENABLED` exists), so a video
        outage degrades this one acceptance to a Callback and the Visitor is told a Strategist
        will reach out — with the Lead already captured.
        """
        try:
            return await rooms.create_room(request_id)
        except VideoRoomError:
            # The vendor's own words never reach the Visitor, and never reach a log line
            # either — the exception is a `repr` of somebody else's API.
            logger.warning(
                "A video room could not be opened; the Hand-over degrades to a Callback",
                extra={"request_id": request_id},
            )
            return None

    @router.post("/handover/{request_id}/accept")
    async def accept(request: Request, request_id: str) -> HandoverStatus:
        """The Visitor pressed Yes.

        Mode is decided here and nowhere else, because Availability is a live fact: a
        Strategist can go offline between the offer and the answer, and the answer is what the
        Visitor is about to be promised.

        In `video` mode the room is created *before* the write, so the acceptance either
        answers with a room the Visitor can open or is a Callback — never a `video` Hand-over
        with nowhere to go.
        """
        stored = await owned_request(request, request_id)
        accepted = validated(stored, "accepted_by_user")
        online = await store.any_strategist_online()
        mode: HandoverMode = "video" if live_handover_enabled and online else "callback"
        room = await opened_room(request_id) if mode == "video" else None
        if mode == "video" and room is None:
            mode = "callback"
        # Both hops are validated against the machine, then written once. `accepted_by_user` is
        # a moment, not a state anybody waits in: persisting it separately would mean a crash
        # between the two writes could strand a request there — a state only the Visitor's
        # browser could move on from, and it has already had its answer.
        moved = validated(accepted, "pending_strategist", mode)
        pending = await store.update_handover(moved.id, moved.state, moved.mode, room=room)
        logger.info("Hand-over accepted", extra={"request_id": pending.id, "handover_mode": mode})
        return status_of(pending)

    @router.get("/handover/{request_id}")
    async def read_status(request: Request, request_id: str) -> HandoverStatus:
        """What the widget polls while a video Hand-over waits for a Strategist.

        The join timeout is answered here and nowhere else. It is lazy on purpose: a
        background scheduler would be a second process to run, a second clock to trust and a
        job per Handover Request that nobody is waiting on any more, where the Visitor who
        cares is already asking this question every five seconds. Past the window the request
        becomes `no_strategist_available` with the mode flipped to `callback`, in this same
        read — so the answer the Visitor gets is the answer that was written.
        """
        stored = await owned_request(request, request_id)
        if join_timed_out(stored, now(), join_timeout_seconds):
            gave_up = validated(stored, "no_strategist_available", "callback")
            stored = await store.update_handover(gave_up.id, gave_up.state, gave_up.mode)
            logger.info(
                "No Strategist joined in time; the Hand-over is a Callback",
                extra={"request_id": stored.id},
            )
        return status_of(stored)

    @router.post("/handover/{request_id}/decline")
    async def decline(request: Request, request_id: str) -> HandoverStatus:
        """The Visitor pressed "Keep chatting". The conversation carries on exactly as it was;
        the request is recorded as declined so the Console does not show it as work."""
        stored = await owned_request(request, request_id)
        moved = validated(stored, "declined")
        declined = await store.update_handover(moved.id, moved.state, moved.mode)
        logger.info("Hand-over declined", extra={"request_id": declined.id})
        return status_of(declined)

    @router.post("/leads")
    async def capture(request: Request, details: ContactDetails) -> CapturedLead:
        """The "Your details" card.

        The second path to a Lead and deliberately the same merge as the first: `capture_lead`
        folds what the Assistant learned into the Session's one Lead, and so does this, so a
        Visitor who typed their email into the card and mentioned their phone in conversation
        is one person in the Console rather than two rows.
        """
        session_id = read_session_id(request, cookie_secret)
        if session_id is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, NO_SESSION)
        existing = await store.get_lead(session_id)
        lead = await store.upsert_lead(
            session_id,
            merged_lead(existing, session_id, details.model_dump(), qualification_threshold),
        )
        # The Handover Request carries a copy of the Lead so the Console's queue is one read;
        # details typed after accepting would otherwise leave a Callback with no name on it.
        offered = await store.handover_for_session(session_id)
        if offered is not None:
            await store.update_handover(
                offered.id, offered.state, offered.mode, lead_snapshot(lead)
            )
        logger.info("Contact Details shared", extra={"qualification_score": lead.score})
        return CapturedLead(
            lead=LeadContact(name=lead.name, email=lead.email, company=lead.company),
            score=lead.score,
            qualified=lead.qualified,
        )

    @router.get("/availability")
    async def availability() -> PublicAvailability:
        """What the chat header's presence line reads.

        Public, because the chat panel is public. It answers one boolean about the team and
        names nobody: which Strategists exist, who they are and who is at their desk are all
        behind the Console's allowlist.
        """
        return PublicAvailability(any_online=await store.any_strategist_online())

    return router
