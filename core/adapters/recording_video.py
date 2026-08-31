"""The `VideoRooms` seam recorded in memory — a Live Hand-over with no Daily.co.

The counterpart of the in-memory `Notifier`: no unit test may reach Daily (constraint 4), and
the two things an HTTP test needs to know about a room are *was one asked for* and *was it
asked for exactly once* — so this keeps the request ids it was given and hands back a room
whose URL is obviously not a real one.

`FailingVideoRooms` is the other half of the same story, and the more important one: creating
a room can fail, and when it does the acceptance has to degrade to a Callback rather than
promise the Visitor a call with no room behind it.
"""

from datetime import UTC, datetime, timedelta

from core.video import Room, VideoRoomError, room_name

# Obviously not a real Daily domain, for the same reason a fixture's email is example.com.
FAKE_DOMAIN = "cadre-demo.daily.invalid"

REFUSED = "The video provider refused to create a room."


class RecordingVideoRooms:
    """Hands back a room and remembers who asked for one."""

    def __init__(self, *, ttl_seconds: int = 3600) -> None:
        self.requested: list[str] = []
        self._ttl_seconds = ttl_seconds

    async def create_room(self, request_id: str) -> Room:
        self.requested.append(request_id)
        name = room_name(request_id)
        return Room(
            url=f"https://{FAKE_DOMAIN}/{name}",
            name=name,
            expires_at=datetime.now(tz=UTC) + timedelta(seconds=self._ttl_seconds),
        )


class FailingVideoRooms:
    """Every room fails — the outage the Callback fallback exists for."""

    def __init__(self) -> None:
        self.requested: list[str] = []

    async def create_room(self, request_id: str) -> Room:
        self.requested.append(request_id)
        raise VideoRoomError(REFUSED)
