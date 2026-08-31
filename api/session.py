"""The Session cookie: an opaque, server-issued id, and nothing else.

A Session is anonymous — no account, no personal data in the cookie, nothing a browser script
can read. The id is the key of the `ConversationStore` and, from ticket 03, a Firestore
document id, so an id that arrives from a client is only honoured if it still looks like one we
issued; anything else earns a fresh Session rather than a lookup of someone else's.
"""

import re
import secrets

from starlette.requests import Request
from starlette.responses import Response

SESSION_COOKIE = "cadre_session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 7

_ISSUED_ID = re.compile(r"^[A-Za-z0-9_-]{16,64}$")


def new_session_id() -> str:
    return secrets.token_urlsafe(24)


def read_session_id(request: Request) -> str | None:
    candidate = request.cookies.get(SESSION_COOKIE, "")
    return candidate if _ISSUED_ID.match(candidate) else None


def set_session_cookie(response: Response, session_id: str, *, secure: bool) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        session_id,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )
