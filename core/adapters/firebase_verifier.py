"""The Firebase `TokenVerifier` — the one production implementation of the seam.

The browser signs in with Google through Firebase Auth and sends the resulting ID token as a
bearer credential; this turns it back into the Strategist who signed in. Verification is
`google-auth`'s: the token's signature is checked against Google's published certificates, its
audience against this Firebase project, and its expiry against the clock. There is no session
store on our side and nothing to revoke — the token expires in an hour and the browser refreshes
it (ADR-0010).

`google.oauth2.id_token` is imported here and nowhere else (constraint 7). The verification
itself is a blocking call that may fetch and cache Google's certificates, so it is run on a
worker thread: a Console request must not stall the event loop serving a Visitor's Turn.
"""

from typing import Any

import anyio.to_thread
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from core.auth import InvalidTokenError, StrategistIdentity, identity_from_claims
from core.logging import get_logger

logger = get_logger("firebase")


class FirebaseTokenVerifier:
    """Verifies Firebase ID tokens issued for one Firebase project."""

    def __init__(self, *, project_id: str) -> None:
        self._project_id = project_id
        # One transport, reused: it holds the cache of Google's signing certificates, and a
        # fresh one per request would fetch them per request.
        self._transport = google_requests.Request()

    async def verify(self, id_token: str) -> StrategistIdentity:
        claims = await anyio.to_thread.run_sync(self._verify, id_token)
        return identity_from_claims(claims)

    def _verify(self, id_token: str) -> dict[str, Any]:
        try:
            # `google-auth` ships no type information, so this call is untyped to mypy; the
            # ignore is on the one line rather than relaxing strictness for the module.
            claims = google_id_token.verify_firebase_token(  # type: ignore[no-untyped-call]
                id_token, self._transport, audience=self._project_id
            )
        except (ValueError, GoogleAuthError) as rejected:
            # Expired, wrong audience, wrong signature, not a JWT at all — all one case to the
            # caller, and the reason stays in the log rather than in the HTTP response.
            logger.warning("Firebase ID token rejected", extra={"reason": type(rejected).__name__})
            raise InvalidTokenError("The Firebase ID token could not be verified.") from None
        if not isinstance(claims, dict):
            raise InvalidTokenError("The Firebase ID token carried no claims.")
        return claims
