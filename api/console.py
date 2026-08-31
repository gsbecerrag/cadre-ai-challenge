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

from core.auth import (
    InvalidTokenError,
    StrategistIdentity,
    TokenVerifier,
    is_allowlisted,
)
from core.logging import get_logger
from core.qualification import present_signals
from core.store import CONTACT_DETAIL_NAMES, DEFAULT_LEAD_PAGE, ConversationStore, Lead

BEARER = "bearer"
# Returned with every 401 so a browser client can tell "sign in again" from "you are not one
# of ours", which is the 403 below.
AUTHENTICATE_HEADER = {"WWW-Authenticate": "Bearer"}

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

    # Written out at every endpoint rather than aliased: the annotation *is* the access
    # control, and an endpoint added here without it would be a public one.
    router = APIRouter(prefix="/console", tags=["console"])

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
    async def list_leads(
        strategist: Annotated[StrategistIdentity, Depends(current_strategist)],
    ) -> ConsoleLeads:
        leads = await store.list_leads(DEFAULT_LEAD_PAGE)
        return ConsoleLeads(leads=[console_lead(lead) for lead in leads])

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
