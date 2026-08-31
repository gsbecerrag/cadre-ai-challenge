"""The Session cookie: an opaque, server-issued id, and nothing else.

A Session is anonymous — no account, no personal data in the cookie, nothing a browser script
can read. The id is the key of the `ConversationStore` and, from ticket 03, a Firestore
document id, so an incoming cookie is checked for *shape* before it is used as one: a
well-formed opaque id is accepted, anything else earns a fresh Session.

That is a check on form, not on issuance — the cookie is unsigned, so a client can mint a
well-formed id and read the Session it names. Nothing in a Session is private today (the
Assistant answers the same public Knowledge Base to everyone) but this stops being enough as
soon as a Lead is attached to one. Signing arrives with ticket 03, which is where the
`SESSION_COOKIE_SECRET` in `.env.example` is for.
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
