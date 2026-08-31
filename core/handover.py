"""The Handover Request and the state machine it may move through.

Pure, and deliberately so. A Hand-over spends a Strategist's time, so every move is validated
server-side (ADR-0007) — and validation that is a table plus a function is a thing a reviewer
can read in one sitting and a test can sweep exhaustively, where the same rules spread across
two endpoints and a browser would be a thing nobody can check.

The machine the spec fixes:

    offered ──▶ accepted_by_user ──▶ pending_strategist ──▶ strategist_joined ──▶ in_call ──▶ ended
       │                                     │
       └──▶ declined                         └──▶ no_strategist_available

`ended`, `declined` and `no_strategist_available` are terminal. Nothing re-enters a state it is
already in, so a double-clicked button or a retried request is refused rather than silently
repeated.

`mode` is not a state: one Handover Request type carries `video` or `callback`, decided at the
moment the Visitor accepts (docs/design/README.md ruling), and the Console's Callbacks tab is
the `callback` filter of the same collection. The display labels a Strategist reads — Pending,
In call, Ended, Declined, Callback — are derived from `state` and `mode` in the Console, so the
data model keeps the eight names the spec uses and the screen keeps the five the design draws.
"""

import secrets
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Literal, get_args

# One Handover Request type carries both modes rather than two entities (the design ruling):
# `video` is a call in the chat panel now, `callback` is a Strategist reaching out later.
HandoverMode = Literal["video", "callback"]

HandoverState = Literal[
    "offered",
    "accepted_by_user",
    "pending_strategist",
    "strategist_joined",
    "in_call",
    "ended",
    "declined",
    "no_strategist_available",
]

HANDOVER_STATES: tuple[HandoverState, ...] = get_args(HandoverState)

# Every move a Handover Request may make. A state that is not a key here is terminal, and a
# pair that is not in it is refused — including every self-transition.
TRANSITIONS: Mapping[str, tuple[HandoverState, ...]] = {
    "offered": ("accepted_by_user", "declined"),
    "accepted_by_user": ("pending_strategist",),
    "pending_strategist": ("strategist_joined", "no_strategist_available"),
    "strategist_joined": ("in_call",),
    "in_call": ("ended",),
}

# 144 bits, urlsafe-base64: the id travels in the URL the Visitor's browser posts to, and
# holding it is half of what proves the Session owns the request (the cookie is the other
# half), so it is minted the way a Session id is rather than counted up.
_REQUEST_ID_BYTES = 18

# How long a Visitor watches a spinner before the Hand-over degrades to a Callback, when the
# deployment configures nothing. Two minutes is longer than a Strategist with the Console open
# needs to press one button, and short enough that a Visitor does not give up first.
DEFAULT_JOIN_TIMEOUT_SECONDS = 120


class InvalidTransitionError(ValueError):
    """A move the state machine does not allow. The API answers it with 409."""


@dataclass(frozen=True)
class LeadSnapshot:
    """The Lead as it stood when the Hand-over was offered, copied onto the request.

    A copy rather than a reference, so the Console's queue is one read per screen instead of a
    join across two collections for every row, and so a Strategist reading a request from last
    week sees what the Assistant actually knew when it offered. Contact Details are raw
    (ADR-0006): a tokenised email is a Callback nobody can return.
    """

    name: str = ""
    email: str = ""
    company: str = ""
    phone: str = ""
    role: str = ""
    signals: Mapping[str, str] = field(default_factory=dict)
    score: int = 0
    qualified: bool = False


@dataclass(frozen=True)
class HandoverRequest:
    """One offered Hand-over: its state, its mode, and the Lead a Strategist would pick up."""

    id: str
    session_id: str
    state: HandoverState = "offered"
    mode: HandoverMode | None = None
    # The one short line the Assistant phrased the offer with, in the Visitor's language. The
    # widget falls back to its own copy when this is empty, so a model that called the tool
    # with no argument still produces the card the design draws.
    prompt: str = ""
    lead: LeadSnapshot = field(default_factory=LeadSnapshot)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    # Ticket 06 fills this in; it is here from the start because the Console's request detail
    # draws a Trace row whether or not there is a Trace to link yet.
    trace_id: str | None = None
    # The Daily room this Hand-over is held in, created at acceptance in `video` mode and
    # empty in every other mode and state. Both sides join the same URL: the Visitor through
    # the iframe in the chat panel, the Strategist through the one in the Console.
    room_url: str = ""
    room_expires_at: datetime | None = None
    # Who claimed it. The Visitor's panel says "You're being assisted by ..." with this name,
    # so it is the Strategist's display name and not their uid or their email — the Visitor is
    # meeting a person, not an account (docs/design/DESIGN-BRIEF.md §2.6).
    strategist_name: str = ""


def new_request_id() -> str:
    return secrets.token_urlsafe(_REQUEST_ID_BYTES)


def may_transition(state: str, target: str) -> bool:
    """Whether the machine allows this move. Unknown states are simply not allowed."""
    return target in TRANSITIONS.get(state, ())


def transition(
    request: HandoverRequest,
    target: HandoverState,
    mode: HandoverMode | None = None,
) -> HandoverRequest:
    """The request in its next state, or `InvalidTransitionError`.

    Returns a new value and leaves its argument alone: an endpoint validates the move before
    it writes, and a validation that mutated the request would leave the new state behind even
    when the write that followed it failed. `mode` is set only when this move decides it — a
    Callback that later runs out of Strategists is still a Callback.
    """
    if not may_transition(request.state, target):
        raise InvalidTransitionError(
            f"A Handover Request in {request.state!r} cannot move to {target!r}."
        )
    return replace(request, state=target, mode=mode if mode is not None else request.mode)


def join_timed_out(request: HandoverRequest, now: datetime, timeout_seconds: int) -> bool:
    """Whether a video Hand-over has waited longer than a Visitor should for a Strategist.

    The timeout is a question, not a scheduler: it is asked when the widget polls the
    request's status, and the answer is what turns `pending_strategist` into
    `no_strategist_available` with the mode flipped to `callback` (ADR-0007). No background
    job, no second clock, and nothing to keep running between requests — a Visitor who closed
    the tab is a Visitor nobody has to time out.

    Only a `video` request in `pending_strategist` can time out. A Callback is already the
    fallback, so closing one would take a call a Strategist still owes away from them; a
    request somebody has joined is a call, not a wait.
    """
    if request.state != "pending_strategist" or request.mode != "video":
        return False
    waiting_since = request.updated_at or request.created_at
    if waiting_since is None:
        # Nothing to measure from is not evidence that nobody came.
        return False
    if waiting_since.tzinfo is None:
        # Everything this service writes is UTC; a store that hands back a naive datetime must
        # not make the comparison raise in the middle of a Visitor's status poll.
        waiting_since = waiting_since.replace(tzinfo=UTC)
    return (now - waiting_since).total_seconds() > timeout_seconds
