"""The Daily.co `VideoRooms` — the one production implementation of the seam (ADR-0007).

Raw HTTP against Daily's REST API, no vendor SDK, for the same reason the OpenRouter adapter
is raw HTTP: the whole integration is one POST, and an SDK would be a dependency, an import
and a second way to configure a key in exchange for nothing.

    POST https://api.daily.co/v1/rooms
    Authorization: Bearer <DAILY_API_KEY>
    {"name": "cadre-<request id>", "properties": {"exp": <unix>, "enable_prejoin_ui": true}}

Two properties and no more. `exp` is what makes the room ephemeral — an hour from creation,
after which the URL is dead, so a link that leaks out of a transcript is not a way into
anybody's call. `enable_prejoin_ui` gives the Visitor the camera-and-microphone check Daily
draws before they are on camera, which is the difference between joining a call and being
suddenly in one.

Nothing here decides what to do about a failure: it raises `VideoRoomError` and the
acceptance in `api/handover.py` degrades that Hand-over to a Callback. A video outage must
never block lead capture (constraint from the spec, and the whole point of the flag).

Daily is named in this module and nowhere else (constraint 7).
"""

import time
from datetime import UTC, datetime

import httpx2

from core.logging import get_logger
from core.video import Room, VideoRoomError, room_name

DEFAULT_BASE_URL = "https://api.daily.co/v1"
ROOMS = "/rooms"

# How long a room lives. Long enough for a real conversation, short enough that the URL is
# worthless by the time it could be found in a log or a screenshot.
ROOM_TTL_SECONDS = 3600

# Creating a room is one small POST in front of a Visitor who has just pressed Yes and is
# watching a spinner, so the budget is short: past this the Callback is the better answer.
TIMEOUT = httpx2.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)

logger = get_logger("daily")


class DailyVideoRooms:
    """Creates one Daily room per Handover Request."""

    def __init__(
        self,
        *,
        api_key: str,
        domain: str,
        base_url: str = DEFAULT_BASE_URL,
        ttl_seconds: int = ROOM_TTL_SECONDS,
    ) -> None:
        self._domain = domain.strip().rstrip("/")
        self._ttl_seconds = ttl_seconds
        self._client = httpx2.AsyncClient(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=TIMEOUT,
        )

    async def create_room(self, request_id: str) -> Room:
        name = room_name(request_id)
        expires_at = int(time.time()) + self._ttl_seconds
        try:
            response = await self._client.post(
                ROOMS,
                json={
                    "name": name,
                    "properties": {"exp": expires_at, "enable_prejoin_ui": True},
                },
            )
        except httpx2.HTTPError as unreachable:
            # The vendor's words never reach the Visitor; the request id does, because that is
            # what a Strategist would use to find the Hand-over this happened to.
            logger.warning(
                "Daily could not be reached",
                extra={"request_id": request_id, "handover_mode": "video"},
            )
            raise VideoRoomError(f"Daily could not be reached: {unreachable!r}") from unreachable
        # Anything that is not a 2xx, including a redirect: this client does not follow them,
        # so a 3xx here is a room that was not created and a body that is not a room.
        if not (200 <= response.status_code < 300):
            logger.warning(
                "Daily refused to create a room",
                extra={"request_id": request_id, "status": response.status_code},
            )
            raise VideoRoomError(f"Daily answered {response.status_code} creating a room.")
        try:
            document = response.json()
        except ValueError as unreadable:
            # A 200 whose body is not JSON — a proxy's error page, a truncated response. Every
            # way this call can fail has to leave by the same door, because the caller degrades
            # a `VideoRoomError` to a Callback and lets anything else become a lost acceptance.
            logger.warning(
                "Daily answered with something that is not JSON",
                extra={"request_id": request_id, "status": response.status_code},
            )
            raise VideoRoomError("Daily's answer could not be read as JSON.") from unreadable
        if not isinstance(document, dict):
            logger.warning(
                "Daily answered with JSON that is not a room",
                extra={"request_id": request_id, "status": response.status_code},
            )
            raise VideoRoomError("Daily's answer was not a room document.")
        url = str(document.get("url") or f"https://{self._domain}/{name}")
        logger.info("Video room created", extra={"request_id": request_id, "room": name})
        return Room(
            url=url,
            name=str(document.get("name") or name),
            expires_at=datetime.fromtimestamp(expires_at, tz=UTC),
        )
