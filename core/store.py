"""The `ConversationStore` seam: a Session's message history, and nothing else.

The API is stateless — every Turn loads the Session and writes it back (ADR-0003) — so this is
the only place conversational state lives. One production implementation (Firestore, ticket 03)
and one test implementation (in memory) sit behind it. Reads are always scoped to one Session
id, which is what keeps one Visitor's conversation out of another's.
"""

from collections.abc import Sequence
from typing import Protocol

from core.provider import ModelMessage


class ConversationStore(Protocol):
    """The message history of one Session."""

    async def load(self, session_id: str) -> tuple[ModelMessage, ...]:
        """Every message in the Session, oldest first. An unknown Session is empty."""
        ...

    async def append(self, session_id: str, messages: Sequence[ModelMessage]) -> None:
        """Add messages to the end of the Session's history."""
        ...
