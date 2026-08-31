"""The `ConversationStore` seam: a Session's message history, and the Lead it produced.

The API is stateless — every Turn loads the Session and writes it back (ADR-0003) — so this is
the only place conversational state lives. One production implementation (Firestore, ticket 03)
and one test implementation (in memory) sit behind it. Reads are always scoped to one Session
id, which is what keeps one Visitor's conversation out of another's.

A Lead is keyed by its Session too, and lives behind the same seam rather than a second one:
it is written in the middle of a Turn by the `capture_lead` tool, from the same request, on the
same database, under the same Session id. A second Protocol would buy one more thing to wire up
and nothing else.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol

from core.provider import ModelMessage

# The Contact Details a Lead carries, kept raw: a tokenised email is a Lead no Strategist can
# call back (ADR-0006). These are `capture_lead`'s Contact Detail arguments, in the order the
# Console shows them.
CONTACT_DETAIL_NAMES: tuple[str, ...] = ("name", "email", "company", "phone", "role")


@dataclass(frozen=True)
class Lead:
    """A Visitor who has shared Contact Details, with the Qualification Signals collected.

    One Lead per Session: the Visitor gives their name in one Turn and their phone number three
    Turns later, and both belong to the same person. `signals` holds what the Assistant learned,
    one short phrase per Qualification Signal, and `score` is the count of them present —
    computed in code before the Lead is written, never sent by the model (ADR-0009).
    """

    session_id: str
    name: str = ""
    email: str = ""
    company: str = ""
    phone: str = ""
    role: str = ""
    signals: Mapping[str, str] = field(default_factory=dict)
    score: int = 0
    qualified: bool = False

    @property
    def contact_details(self) -> Mapping[str, str]:
        """The Contact Details that are actually filled in."""
        return {
            name: value
            for name in CONTACT_DETAIL_NAMES
            if (value := str(getattr(self, name, "") or "").strip())
        }


class ConversationStore(Protocol):
    """The message history of one Session, and the Lead captured from it."""

    async def load(self, session_id: str) -> tuple[ModelMessage, ...]:
        """Every message in the Session, oldest first. An unknown Session is empty."""
        ...

    async def append(self, session_id: str, messages: Sequence[ModelMessage]) -> None:
        """Add messages to the end of the Session's history."""
        ...

    async def get_lead(self, session_id: str) -> Lead | None:
        """The Session's Lead, or `None` while the Visitor has shared no Contact Details."""
        ...

    async def upsert_lead(self, session_id: str, lead: Lead) -> Lead:
        """Write the Session's one Lead, replacing what was there, and return what was written.

        The caller merges: it reads the Lead, folds the new Contact Details and Qualification
        Signals into it, counts the score, and writes the whole thing back — so the merge rule
        and the score live in one place instead of once per implementation of this seam.
        """
        ...
