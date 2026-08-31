"""The `TokenVerifier` seam and the allowlist: who may open the Console.

The Console shows every Lead's raw Contact Details, so the whole authorisation model is two
questions asked on every request: *is this a real Firebase ID token* (the verifier), and *is
the email in it one of ours* (the allowlist). ADR-0010 chose that over a session store, an
identity platform or a shared password, because an allowlist of a handful of Strategists is
genuinely the entire policy.

The verifier is a seam for the same reason the `ModelProvider` is: verifying a Firebase token
is a network call to Google's public keys, and constraint 4 says no unit test may make one.
The production implementation is `core.adapters.firebase_verifier`; the fakes in
`core.adapters.fake_verifier` are what the HTTP tests and the local demo run on.

The two pure functions below are the policy itself, kept out of the adapters and out of the
request handler so they can be tested for the case that matters — an empty allowlist admits
nobody — rather than exercised through a signed token nobody can mint offline.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol


class InvalidTokenError(Exception):
    """The credential presented is not a usable Strategist identity.

    Absent, malformed, expired, signed by the wrong key, or missing the claims the allowlist
    is checked against. Deliberately one exception: the difference between them is useful in a
    log line and dangerous in an HTTP response, where it tells an attacker which half of the
    guess was right.
    """


@dataclass(frozen=True)
class StrategistIdentity:
    """The Strategist behind a request: their Firebase uid, their email, their display name.

    The uid is the stable one — it is what a presence document is keyed by and what a claimed
    Handover Request will carry (ticket 11) — because a person's email can be reassigned and
    their name can change.
    """

    uid: str
    email: str
    name: str = ""

    @property
    def initial(self) -> str:
        """The letter the Console's avatar circle shows."""
        return (self.name or self.email or "?")[0].upper()


class TokenVerifier(Protocol):
    """Turns the credential on a Console request into the Strategist who sent it."""

    async def verify(self, id_token: str) -> StrategistIdentity:
        """The Strategist the token identifies, or `InvalidTokenError`.

        Async because the production implementation talks to the network (Google's signing
        keys) and a Console request must not block the event loop while it does.
        """
        ...


class ClosedTokenVerifier:
    """The verifier a deployment with no allowlist gets: nothing is a Strategist.

    Not a test double — it is the honest implementation of "this deployment has no Console".
    With `ADMIN_ALLOWED_EMAILS` unset there is nobody the allowlist could admit, so there is
    nothing for a real verifier to do, and building one would demand a Firebase project from
    every developer and every CI run that never opens the Console.
    """

    async def verify(self, id_token: str) -> StrategistIdentity:
        raise InvalidTokenError("No Strategist allowlist is configured on this deployment.")


def parse_allowlist(configured: str) -> frozenset[str]:
    """The `ADMIN_ALLOWED_EMAILS` value as a set of comparable emails.

    Normalised — trimmed and case-folded — because the variable is typed by a human into a
    deploy command, and a Strategist locked out by a capital letter looks exactly like a
    broken sign-in.
    """
    return frozenset(
        folded for entry in configured.split(",") if (folded := entry.strip().casefold())
    )


def is_allowlisted(email: str, allowlist: frozenset[str]) -> bool:
    """Whether this email may open the Console.

    An empty allowlist admits nobody. That is the important direction: a deploy that forgets
    the variable must close the Console rather than open it to the internet.
    """
    return email.strip().casefold() in allowlist


def identity_from_claims(claims: Mapping[str, Any]) -> StrategistIdentity:
    """The Strategist a verified token's claims describe.

    The email must be present and verified: the allowlist is a list of emails, so an
    unverified `email` claim is an allowlist bypass — an account created against some other
    provider could assert an address it does not own. Firebase sets `email_verified` for
    Google sign-in, so requiring it costs a real Strategist nothing.
    """
    uid = str(claims.get("sub") or claims.get("user_id") or "").strip()
    email = str(claims.get("email") or "").strip().casefold()
    if not uid or not email:
        raise InvalidTokenError("The token carries no Strategist uid or no email address.")
    if not claims.get("email_verified", False):
        raise InvalidTokenError("The token's email address is not verified.")
    name = str(claims.get("name") or "").strip() or email.split("@", 1)[0]
    return StrategistIdentity(uid=uid, email=email, name=name)
