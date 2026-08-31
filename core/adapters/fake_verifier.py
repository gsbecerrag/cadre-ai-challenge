"""`TokenVerifier` implementations that need no network — the test double and the demo one.

Verifying a real Firebase ID token means fetching Google's signing keys, which no unit test
may do (constraint 4) and no reviewer should have to arrange a Google Workspace account for.
Two fakes, deliberately separate, because they exist for different reasons:

- `ScriptedTokenVerifier` — the S1 tests' double. A closed map of token to Strategist; anything
  not in it is rejected, which is what an expired or forged token looks like from the API.
- `DevTokenVerifier` — the local demo's. Decodes `fake:<email>` into a Strategist so the
  Console shell can be opened, screenshotted and clicked through without Google sign-in. It is
  reachable only when `CONSOLE_AUTH=fake` *and* `ENV=development`; `core.config` refuses to
  build production settings that select it, because it accepts an identity anyone can type.
"""

import hashlib
from collections.abc import Mapping

from core.auth import InvalidTokenError, StrategistIdentity

# The prefix a `DevTokenVerifier` credential must carry, so a token meant for it can never be
# mistaken for — or mistaken as — a real Firebase ID token.
DEV_TOKEN_PREFIX = "fake:"


class ScriptedTokenVerifier:
    """A fixed map of ID token to the Strategist it identifies."""

    def __init__(self, identities: Mapping[str, StrategistIdentity]) -> None:
        self._identities = dict(identities)

    async def verify(self, id_token: str) -> StrategistIdentity:
        identity = self._identities.get(id_token)
        if identity is None:
            raise InvalidTokenError("Unknown ID token.")
        return identity


class DevTokenVerifier:
    """Turns `fake:<email>` — optionally `fake:<email>:<name>` — into a Strategist.

    The uid is derived from the email so that the same demo Strategist keeps the same presence
    document across restarts, the way a real Firebase uid would.
    """

    async def verify(self, id_token: str) -> StrategistIdentity:
        if not id_token.startswith(DEV_TOKEN_PREFIX):
            raise InvalidTokenError("Not a development credential.")
        email, _, name = id_token.removeprefix(DEV_TOKEN_PREFIX).partition(":")
        email = email.strip().casefold()
        if "@" not in email:
            raise InvalidTokenError("A development credential must carry an email address.")
        digest = hashlib.sha256(email.encode("utf-8")).hexdigest()[:16]
        return StrategistIdentity(
            uid=f"dev-{digest}", email=email, name=name.strip() or email.split("@", 1)[0]
        )
