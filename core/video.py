"""The `VideoRooms` seam: one call room per Handover Request.

A Live Hand-over is a video call that opens inside the chat panel, and the room it opens is
the one thing in this feature that has to be bought from somebody (ADR-0007 chose Daily.co,
because an anonymous Visitor must not meet a lobby or a sign-in). So it is a seam, for the
same two reasons every other one is: no unit test may reach Daily (constraint 4), and the
vendor is named in exactly one module (constraint 7).

The seam is deliberately one method. Everything the product does with a room — when it is
created, what happens when creating it fails, who is told about it — is a decision in
`api/handover.py` and `api/console.py`, where it can be read next to the state machine it
belongs to. A room here is a URL, a name and the moment it stops working.

Three implementations: `DailyVideoRooms` (core/adapters/daily_video.py, the one production
one), a recording fake for the HTTP tests, and `NoVideoRooms` below — what a deployment with
the flag off or no key gets, where being called at all is a bug.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

# The design draws the room as `daily.co/cadre-{id}` (docs/design/DESIGN-BRIEF.md §3.1), so a
# Strategist reading the Console's banner can match a room to the request it belongs to
# without looking anything up.
ROOM_PREFIX = "cadre-"

# Daily accepts letters, digits, `-` and `_` in a room name. A request id is already
# url-safe base64, so this only ever fires on an id from somewhere else — and it replaces
# rather than strips, because two ids that differ only in a stripped character would
# otherwise become one room with two Visitors in it.
UNSAFE_IN_A_ROOM_NAME = re.compile(r"[^a-z0-9_-]")


class VideoRoomError(RuntimeError):
    """A room could not be created. The Hand-over degrades to a Callback, never to nothing."""


@dataclass(frozen=True)
class Room:
    """One video room: where to join it, what it is called, and when it stops working."""

    url: str
    name: str
    expires_at: datetime


class VideoRooms(Protocol):
    """Opens one room per Handover Request."""

    async def create_room(self, request_id: str) -> Room:
        """The room this Handover Request will be held in, or `VideoRoomError`.

        Called once, at the moment the Visitor accepts, so the URL is already on the request
        when the widget asks for its status.
        """
        ...


def room_name(request_id: str) -> str:
    """The room name for a Handover Request: its id, in a form a URL can carry.

    Lower-cased, which is safe for uniqueness because request ids carry 144 bits of
    randomness — two that differ only in case is not a thing that happens — and worth it
    because the name is read aloud from the Console's banner and typed into a browser.
    """
    if not request_id.strip():
        raise VideoRoomError("A room needs a Handover Request to belong to.")
    return ROOM_PREFIX + UNSAFE_IN_A_ROOM_NAME.sub("-", request_id.strip().casefold())


class NoVideoRooms:
    """The seam for a deployment that has no video: calling it is a bug, and says so.

    Not a silent no-op. With `LIVE_HANDOVER_ENABLED` off or no Daily key, the mode never
    resolves to `video` and nothing should ever ask for a room — so a call that arrives here
    means the gate above it is broken, and a `VideoRoomError` degrades that acceptance to a
    Callback rather than promising a call with no room behind it.
    """

    async def create_room(self, request_id: str) -> Room:
        raise VideoRoomError(
            "This deployment has no video rooms: LIVE_HANDOVER_ENABLED is off or DAILY_API_KEY "
            "is not set, so every accepted Hand-over is a Callback."
        )
