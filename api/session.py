"""The Session cookie: an opaque, server-issued, signed id, and nothing else.

A Session is anonymous — no account, no personal data in the cookie, nothing a browser script
can read. The id is the key of the `ConversationStore` and a Firestore document id, which makes
it a capability: whoever holds it reads that conversation. So the cookie carries a signature
this service can check, `<id>.<hmac-sha256(id) urlsafe-b64>`, and a cookie that does not verify
is not a Session to look up — it earns a fresh one.

The signature is not encryption: the id is visible in the cookie, and it is meant to be. What
the signature buys is that only this service can mint one, so a Session id cannot be guessed,
enumerated, or handed to a Visitor by a link.
"""

import base64
import hashlib
import hmac
import re
import secrets

from starlette.requests import Request
from starlette.responses import Response

SESSION_COOKIE = "cadre_session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 7

# 192 bits of entropy, urlsafe-base64 without padding.
_SESSION_ID_BYTES = 24
_ISSUED_ID = re.compile(r"^[A-Za-z0-9_-]{16,64}$")


def new_session_id() -> str:
    return secrets.token_urlsafe(_SESSION_ID_BYTES)


def _signature(session_id: str, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), session_id.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def sign_session_id(session_id: str, secret: str) -> str:
    """The cookie value for an id: the id, a dot, and the signature over it."""
    return f"{session_id}.{_signature(session_id, secret)}"


def session_id_from_cookie(cookie: str, secret: str) -> str | None:
    """The id inside a cookie this service signed, or `None` for anything else."""
    session_id, separator, signature = cookie.partition(".")
    if not separator or not _ISSUED_ID.match(session_id):
        return None
    # Constant time, so a signature cannot be discovered one byte at a time.
    if not hmac.compare_digest(signature, _signature(session_id, secret)):
        return None
    return session_id


def read_session_id(request: Request, secret: str) -> str | None:
    return session_id_from_cookie(request.cookies.get(SESSION_COOKIE, ""), secret)


def set_session_cookie(response: Response, session_id: str, *, secret: str, secure: bool) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        sign_session_id(session_id, secret),
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )
