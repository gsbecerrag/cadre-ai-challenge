"""Per-request correlation: assign a request id, bind it for logging, echo it back.

Written as plain ASGI rather than `BaseHTTPMiddleware` because the chat endpoint will hold a
streaming response open for the length of a Turn, which `BaseHTTPMiddleware` buffers.
"""

import time
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from core.logging import get_logger, request_context

REQUEST_ID_HEADER = "x-request-id"
MAX_REQUEST_ID_LENGTH = 128

logger = get_logger("api.request")


class RequestContextMiddleware:
    """Bind a request id for the request's log lines and return it on the response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = Headers(scope=scope).get(REQUEST_ID_HEADER, "")
        request_id = incoming.strip()[:MAX_REQUEST_ID_LENGTH] or uuid4().hex
        status = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                MutableHeaders(scope=message).append(REQUEST_ID_HEADER, request_id)
            await send(message)

        started = time.perf_counter()
        with request_context(request_id=request_id):
            try:
                await self.app(scope, receive, send_with_request_id)
            finally:
                logger.info(
                    "request handled",
                    extra={
                        "method": scope.get("method", ""),
                        "path": scope.get("path", ""),
                        "status": status,
                        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                    },
                )
