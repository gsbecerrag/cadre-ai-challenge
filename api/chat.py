"""`POST /api/chat` — one Turn, streamed as Server-Sent Events.

The response is `text/event-stream` rather than JSON because the Visitor should read the answer
as it is written; that is also why the request-id middleware is plain ASGI (`BaseHTTPMiddleware`
would buffer this response until the Turn ended).

`EventSource` cannot POST, so the browser reads this with `fetch` and a `ReadableStream`.
"""

from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from api.session import new_session_id, read_session_id, set_session_cookie
from core.events import error_event
from core.logging import get_logger, session_context
from core.sse import SSE_HEADERS, SSE_MEDIA_TYPE, format_sse_event
from core.turn import TurnRunner

MAX_MESSAGE_LENGTH = 4000

UNEXPECTED_ERROR_MESSAGE = (
    "Something went wrong on my side. Please try again — or reach the team at "
    "hello@gocadre.ai or (619) 324-3223."
)

logger = get_logger("api.chat")


class TurnRequest(BaseModel):
    """What the chat widget posts: one Visitor message."""

    message: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH, pattern=r"\S")


def create_chat_router(runner: TurnRunner, *, cookie_secret: str, secure_cookie: bool) -> APIRouter:
    router = APIRouter(tags=["chat"])

    @router.post("/chat")
    async def chat(request: Request, turn: TurnRequest) -> StreamingResponse:
        session_id = read_session_id(request, cookie_secret) or new_session_id()

        async def frames() -> AsyncIterator[str]:
            with session_context(session_id):
                try:
                    async for event in runner.run(session_id, turn.message):
                        yield format_sse_event(event)
                except Exception:
                    # The status line is long gone, so a 500 is not available: the only way to
                    # tell the Visitor is an event they can read.
                    logger.exception("Turn crashed")
                    yield format_sse_event(error_event(UNEXPECTED_ERROR_MESSAGE))

        response = StreamingResponse(frames(), media_type=SSE_MEDIA_TYPE, headers=SSE_HEADERS)
        set_session_cookie(response, session_id, secret=cookie_secret, secure=secure_cookie)
        return response

    return router
