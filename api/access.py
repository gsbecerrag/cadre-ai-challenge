"""The Access Code: one shared code between a public URL and a metered model key (ticket 21).

The Assistant is deployed where anyone can reach it and answers with a key that has a small
balance. Nothing about the product needs a login — a Visitor is anonymous by design — but a
key that a stranger's script can drain is a demo that stops mid-sentence. So the two endpoints
that spend the key, a Turn and a Feedback (a thumbs-down runs the Triage Agent), are behind a
code the Cadre team receives privately. It is not authentication: it says nothing about who
the Visitor is, only that they were given the code.

The unlock is a second signed cookie beside the Session's, `cadre_access`, holding an HMAC over
a fixed label under the Session cookie's key. It is deliberately not bound to the Session id: a
Session ends at its Turn cap and a new one begins, and a browser that was given the code stays
unlocked through that. A code is compared in constant time, a wrong one is refused without
saying how it was wrong, and five wrong ones lock further attempts — counted per Session, or
per client address for a caller that presents no Session, so a script cannot walk a short code
by simply dropping its cookies. With no code configured there is no gate at all, which is what
CI, `make dev` and a reviewer's laptop see.
"""

import base64
import hashlib
import hmac
import re

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from api.session import read_session_id
from core.logging import get_logger

ACCESS_COOKIE = "cadre_access"
ACCESS_MAX_AGE_SECONDS = 60 * 60 * 24 * 7
# What the unlock signature is taken over. Bumping the version invalidates every unlock cookie
# at once without touching the Session secret.
_UNLOCK_LABEL = b"cadre_access:v1"
# Same shape as the Session signature: 43 urlsafe-base64 characters, checked before compared.
_SIGNATURE = re.compile(r"^[A-Za-z0-9_-]{43}$")

MAX_ATTEMPTS = 5
# The attempt table lives in the instance's memory. Past this many callers it is forgotten
# wholesale, which costs a locked caller its lock — never a Visitor their access.
_MAX_TRACKED_CALLERS = 10_000
MAX_CODE_LENGTH = 200

ACCESS_CODE_REQUIRED = "access_code_required"
CODE_NOT_ACCEPTED = "That code was not accepted."
TOO_MANY_ATTEMPTS = "Too many attempts. Start a new conversation to try again."

logger = get_logger("api.access")


def unlock_token(secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), _UNLOCK_LABEL, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def is_unlocked(request: Request, secret: str) -> bool:
    presented = request.cookies.get(ACCESS_COOKIE, "")
    if not _SIGNATURE.match(presented):
        return False
    return hmac.compare_digest(presented.encode("ascii"), unlock_token(secret).encode("ascii"))


def set_access_cookie(response: Response, *, secret: str, secure: bool) -> None:
    response.set_cookie(
        ACCESS_COOKIE,
        unlock_token(secret),
        max_age=ACCESS_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )


def caller_key(request: Request, cookie_secret: str) -> str:
    """Who an attempt is counted against: the Session, or the client address without one.

    Cloud Run's frontend appends the real client address as the *last* `X-Forwarded-For`
    element; anything before it is whatever the client chose to send.
    """
    session_id = read_session_id(request, cookie_secret)
    if session_id is not None:
        return f"session:{session_id}"
    forwarded = request.headers.get("x-forwarded-for", "")
    address = forwarded.rsplit(",", 1)[-1].strip() if forwarded else ""
    if not address and request.client is not None:
        address = request.client.host
    return f"address:{address or 'unknown'}"


class AccessGate:
    """What the spending endpoints ask before they do anything else."""

    def __init__(self, *, code: str, cookie_secret: str) -> None:
        self._code = code.strip()
        self._secret = cookie_secret

    @property
    def required(self) -> bool:
        return bool(self._code)

    def unlocked(self, request: Request) -> bool:
        return not self.required or is_unlocked(request, self._secret)

    def check(self, request: Request) -> None:
        """Raise the 401 the widget reads as "show the code field"."""
        if not self.unlocked(request):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, ACCESS_CODE_REQUIRED)

    def accepts(self, code: str) -> bool:
        return hmac.compare_digest(code.strip().encode("utf-8"), self._code.encode("utf-8"))


class AccessRequest(BaseModel):
    """What the widget posts once: the code the Visitor was given."""

    code: str = Field(min_length=1, max_length=MAX_CODE_LENGTH, pattern=r"\S")


class AccessStatus(BaseModel):
    """What the widget reads on load: is there a gate, and is this browser past it."""

    required: bool
    unlocked: bool


def create_access_router(gate: AccessGate, *, cookie_secret: str, secure_cookie: bool) -> APIRouter:
    router = APIRouter(tags=["access"])
    failures: dict[str, int] = {}

    @router.get("/access")
    async def access_status(request: Request) -> AccessStatus:
        return AccessStatus(required=gate.required, unlocked=gate.unlocked(request))

    @router.post("/access", status_code=status.HTTP_204_NO_CONTENT)
    async def unlock(request: Request, submission: AccessRequest) -> Response:
        response = Response(status_code=status.HTTP_204_NO_CONTENT)
        if not gate.required:
            return response
        caller = caller_key(request, cookie_secret)
        if failures.get(caller, 0) >= MAX_ATTEMPTS:
            logger.warning("Access Code attempts exhausted")
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, TOO_MANY_ATTEMPTS)
        if not gate.accepts(submission.code):
            if len(failures) >= _MAX_TRACKED_CALLERS:
                failures.clear()
            failures[caller] = failures.get(caller, 0) + 1
            logger.info("Access Code refused", extra={"attempt": failures[caller]})
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, CODE_NOT_ACCEPTED)
        failures.pop(caller, None)
        set_access_cookie(response, secret=gate._secret, secure=secure_cookie)
        logger.info("Access Code accepted")
        return response

    return router
