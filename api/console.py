"""`/api/console/*` — the endpoints only a Strategist may reach.

Everything here is behind one dependency, `current_strategist`, which asks the two questions
ADR-0010 settled on: is this a token the `TokenVerifier` accepts, and is the email in it on the
allowlist. Missing or unusable credential is 401; a real Google account Cadre does not employ
is 403 — a distinction worth making, because a Strategist who mistyped nothing and simply is
not on the list would otherwise retry the sign-in forever.

The Console reads Leads twice over: once from here, so the first paint needs no Firestore
client and no rules evaluation, and then live from Firestore through a browser listener. Both
paths enforce the same allowlist, which is the price of realtime (ADR-0010) and the reason
`firestore.rules` is rendered from the same environment variable this router reads.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from api.handover import validated
from core.auth import (
    InvalidTokenError,
    StrategistIdentity,
    TokenVerifier,
    is_allowlisted,
)
from core.handover import HandoverMode, HandoverRequest, HandoverState, LeadSnapshot
from core.logging import get_logger
from core.qualification import present_signals
from core.store import (
    CONTACT_DETAIL_NAMES,
    DEFAULT_HANDOVER_PAGE,
    DEFAULT_LEAD_PAGE,
    ConversationStore,
    Lead,
)

BEARER = "bearer"
# Returned with every 401 so a browser client can tell "sign in again" from "you are not one
# of ours", which is the 403 below.
AUTHENTICATE_HEADER = {"WWW-Authenticate": "Bearer"}

NO_SUCH_REQUEST = "There is no Handover Request with that id."

# A Callback has no room to join. The Visitor was promised a phone call, so the refusal says
# what to do instead rather than only what went wrong.
NOT_A_LIVE_HAND_OVER = (
    "This is a Callback, not a Live Hand-over: there is no room to join. Reach the Lead on "
    "the Contact Details on this request."
)

# A request with no mode is one the Visitor has not answered. Calling that a Callback would
# tell a Strategist to go and phone somebody who has not agreed to be phoned.
NOT_ANSWERED_YET = (
    "This Hand-over has not been accepted yet: the Visitor has not answered the offer, so "
    "there is nothing to join and nobody expecting to hear from you."
)

# The two roles a Strategist reads in "Conversation so far". The tool traffic between them is
# not conversation: a `capture_lead` result rendered as a bubble would show a Strategist an
# exchange that never happened.
CONVERSATION_ROLES = ("visitor", "assistant")

NO_CREDENTIAL = (
    "This is Cadre's Strategist Console. Sign in with your Cadre Google account to continue."
)
BAD_CREDENTIAL = "That sign-in could not be verified. Please sign in again."

logger = get_logger("api.console")


class AvailabilityState(BaseModel):
    """Availability as the Console renders it: this Strategist's toggle, and the team's."""

    online: bool
    any_online: bool


class AvailabilityUpdate(BaseModel):
    """What the Availability toggle sends."""

    online: bool


class ConsoleLead(BaseModel):
    """One Lead as the Console's queue card needs it.

    Contact Details are raw and deliberately so (ADR-0006) — this response is the one place
    they are meant to travel, to the one audience allowed to see them. `present_signals` is
    the Qualification Score's own answer to which of the five the Lead carries, in the fixed
    order the Console draws its rows in, so the browser never has to know which arguments of
    `capture_lead` are signals and which are Contact Details.
    """

    session_id: str
    name: str
    email: str
    company: str
    phone: str
    role: str
    signals: dict[str, str]
    present_signals: list[str]
    score: int
    qualified: bool


class ConsoleLeads(BaseModel):
    leads: list[ConsoleLead]


class ConsoleHandover(BaseModel):
    """One Handover Request as the queue card and the Callbacks row need it.

    The Lead travels as the snapshot taken when the Hand-over was offered, in the same shape
    the Leads page already renders — so the Console has one Lead component, and the queue is
    one read per screen rather than a join across two collections for every row.
    """

    request_id: str
    session_id: str
    state: HandoverState
    mode: HandoverMode | None
    prompt: str
    created_at: str | None
    trace_id: str | None
    lead: ConsoleLead
    # The Daily room, and who claimed it. Empty until a Visitor accepts in `video` mode and a
    # Strategist joins — the queue card reads the first to decide whether to draw "Claim &
    # join call", and the detail's in-call banner shows both.
    room_url: str
    strategist_name: str


class ConsoleHandovers(BaseModel):
    handovers: list[ConsoleHandover]


class ConsoleMessage(BaseModel):
    """One line of "Conversation so far"."""

    role: str
    text: str


class ConsoleHandoverDetail(BaseModel):
    """What the request detail draws: the request, the Lead as it stands now, and the
    conversation up to the offer.

    The transcript is read here and not in the browser on purpose: `firestore.rules` denies a
    client every read of `sessions`, because a Session is the Visitor's side of the product,
    and the one audience allowed to see a conversation gets it through this endpoint.
    """

    handover: ConsoleHandover
    lead: ConsoleLead
    conversation: list[ConsoleMessage]


def not_allowlisted(email: str) -> str:
    """The refusal a signed-in stranger reads. It says what happened and what to do."""
    return (
        f"{email} is not on Cadre's Strategist allowlist, so this Console is not available to "
        "this account. If you are a Cadre Strategist, ask for your email to be added; "
        "otherwise the Assistant on cadreai.com is the way in."
    )


def bearer_token(request: Request) -> str:
    """The ID token on the request, or the empty string.

    The scheme is required: a bare token in the header is a client that has misunderstood the
    contract, and treating it as a credential would make the contract two contracts.
    """
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    return token.strip() if scheme.strip().casefold() == BEARER else ""


def create_console_router(
    store: ConversationStore,
    *,
    verifier: TokenVerifier,
    allowlist: frozenset[str],
) -> APIRouter:
    """The Console's routes, with the allowlist and the verifier closed over.

    Both are passed in rather than read from settings here, so the composition root stays the
    only place that decides which `TokenVerifier` is real and the tests can script it.
    """

    async def current_strategist(request: Request) -> StrategistIdentity:
        token = bearer_token(request)
        if not token:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED, NO_CREDENTIAL, headers=AUTHENTICATE_HEADER
            )
        try:
            identity = await verifier.verify(token)
        except InvalidTokenError:
            # One message for expired, forged, malformed and wrong-project: the difference is
            # useful to an attacker and to nobody else.
            logger.warning("Console credential rejected")
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED, BAD_CREDENTIAL, headers=AUTHENTICATE_HEADER
            ) from None
        if not is_allowlisted(identity.email, allowlist):
            # The uid and the email's domain, never the address: enough to tell an outsider
            # from one of Cadre's own with a typo, without writing a person into the logs.
            logger.warning(
                "Console access refused",
                extra={"uid": identity.uid, "email_domain": identity.email.rpartition("@")[2]},
            )
            raise HTTPException(status.HTTP_403_FORBIDDEN, not_allowlisted(identity.email))
        return identity

    # On the router, not on each endpoint: the allowlist check is the Console's defining
    # property, and a route added here that forgot to ask for it would be a public one. FastAPI
    # solves a router-level dependency before the endpoint's own arguments, so this refuses a
    # stranger before it validates their body. The endpoints that need to know *who* signed in
    # ask for the identity as well; it is the same dependency, resolved once per request.
    router = APIRouter(
        prefix="/console", tags=["console"], dependencies=[Depends(current_strategist)]
    )

    @router.get("/availability")
    async def read_availability(
        strategist: Annotated[StrategistIdentity, Depends(current_strategist)],
    ) -> AvailabilityState:
        return AvailabilityState(
            online=await store.get_availability(strategist.uid),
            any_online=await store.any_strategist_online(),
        )

    @router.put("/availability")
    async def set_availability(
        strategist: Annotated[StrategistIdentity, Depends(current_strategist)],
        update: AvailabilityUpdate,
    ) -> AvailabilityState:
        await store.set_availability(strategist, update.online)
        logger.info("Availability set", extra={"uid": strategist.uid, "online": update.online})
        return AvailabilityState(
            online=await store.get_availability(strategist.uid),
            any_online=await store.any_strategist_online(),
        )

    @router.get("/leads")
    async def list_leads() -> ConsoleLeads:
        # No `strategist` argument: every Strategist sees the same queue, so the identity is
        # not needed here — only the admission the router already enforced.
        leads = await store.list_leads(DEFAULT_LEAD_PAGE)
        return ConsoleLeads(leads=[console_lead(lead) for lead in leads])

    @router.get("/handovers")
    async def list_handovers(mode: HandoverMode | None = None) -> ConsoleHandovers:
        """The Handover queue, and — with `mode=callback` — the Callbacks tab.

        One collection and one type, filtered (docs/design/README.md ruling). This is also the
        Console's fallback path: the browser normally holds a realtime listener on
        `handover_requests`, and polls this when the listener cannot start.
        """
        requests = await store.list_handovers(mode, DEFAULT_HANDOVER_PAGE)
        return ConsoleHandovers(handovers=[console_handover(request) for request in requests])

    async def stored_handover(request_id: str) -> HandoverRequest:
        stored = await store.get_handover(request_id)
        if stored is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, NO_SUCH_REQUEST)
        return stored

    @router.post("/handovers/{request_id}/join")
    async def join_call(
        request_id: str,
        strategist: Annotated[StrategistIdentity, Depends(current_strategist)],
    ) -> ConsoleHandover:
        """ "Claim & join call": the Strategist takes the request and enters the room.

        One button in the design (§3.1) and one write here, carrying both hops the machine
        names. `strategist_joined` is a moment, not a state anybody waits in — persisting it
        on its own would put a state nobody was ever in through every open Console's realtime
        listener, and would strand the request there if the second write failed.

        The name written is the verified identity's, never one the browser sent: the Visitor's
        panel says "You're being assisted by ..." with it, and a Strategist's own client is not
        the right authority on who is in the call.
        """
        stored = await stored_handover(request_id)
        if stored.mode is None:
            raise HTTPException(status.HTTP_409_CONFLICT, NOT_ANSWERED_YET)
        if stored.mode != "video":
            raise HTTPException(status.HTTP_409_CONFLICT, NOT_A_LIVE_HAND_OVER)
        joined = validated(stored, "strategist_joined")
        in_call = validated(joined, "in_call")
        claimed = await store.update_handover(
            in_call.id,
            in_call.state,
            in_call.mode,
            # The display name only, never the email. This travels to the Visitor's panel
            # ("You're being assisted by ..."), and a Strategist's work address is not
            # something a stranger on the internet gets because their Google profile has no
            # name on it. Empty is fine: the widget says "a Cadre strategist" in the Visitor's
            # own language, which a string chosen here could not do.
            strategist_name=strategist.name.strip(),
        )
        logger.info(
            "Strategist joined a Live Hand-over",
            extra={"request_id": claimed.id, "uid": strategist.uid},
        )
        return console_handover(claimed)

    @router.post("/handovers/{request_id}/end")
    async def end_call(request_id: str) -> ConsoleHandover:
        """ "End call": the Hand-over is over, for both sides.

        Validated like every other move, so a second click on a stale tab is a 409 rather than
        a request reopened and closed again.
        """
        stored = await stored_handover(request_id)
        ended = validated(stored, "ended")
        closed = await store.update_handover(ended.id, ended.state, ended.mode)
        logger.info("Live Hand-over ended", extra={"request_id": closed.id})
        return console_handover(closed)

    @router.get("/handovers/{request_id}")
    async def read_handover(request_id: str) -> ConsoleHandoverDetail:
        stored = await stored_handover(request_id)
        # The live Lead, because Contact Details keep arriving after the offer — and the
        # snapshot when the Session has none, so the panel is never empty.
        lead = await store.get_lead(stored.session_id)
        history = await store.load(stored.session_id)
        return ConsoleHandoverDetail(
            handover=console_handover(stored),
            lead=(
                console_lead(lead)
                if lead is not None
                else console_lead_from_snapshot(stored.session_id, stored.lead)
            ),
            conversation=[
                ConsoleMessage(role=message.role, text=message.content)
                for message in history
                if message.role in CONVERSATION_ROLES and message.content.strip()
            ],
        )

    return router


def console_lead(lead: Lead) -> ConsoleLead:
    return ConsoleLead(
        session_id=lead.session_id,
        signals=dict(lead.signals),
        present_signals=list(present_signals(lead.signals)),
        score=lead.score,
        qualified=lead.qualified,
        **{name: str(getattr(lead, name, "") or "") for name in CONTACT_DETAIL_NAMES},
    )


def console_lead_from_snapshot(session_id: str, snapshot: LeadSnapshot) -> ConsoleLead:
    """The Lead snapshot on a Handover Request, in the same shape as a live Lead."""
    return ConsoleLead(
        session_id=session_id,
        signals=dict(snapshot.signals),
        present_signals=list(present_signals(snapshot.signals)),
        score=snapshot.score,
        qualified=snapshot.qualified,
        **{name: str(getattr(snapshot, name, "") or "") for name in CONTACT_DETAIL_NAMES},
    )


def console_handover(request: HandoverRequest) -> ConsoleHandover:
    return ConsoleHandover(
        request_id=request.id,
        session_id=request.session_id,
        state=request.state,
        mode=request.mode,
        prompt=request.prompt,
        # ISO 8601 rather than a timestamp, so the browser renders "9:41 AM" from a string it
        # cannot misread as seconds or milliseconds.
        created_at=request.created_at.isoformat() if request.created_at else None,
        trace_id=request.trace_id,
        lead=console_lead_from_snapshot(request.session_id, request.lead),
        room_url=request.room_url,
        strategist_name=request.strategist_name,
    )
