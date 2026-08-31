"""The in-memory `ConversationStore` — the test implementation, and `make dev` without GCP.

Process-local by definition: it is correct for one process and wrong for a Cloud Run service
that scales past one instance, which is exactly why ticket 03 puts Firestore behind the same
seam.
"""

from collections import defaultdict
from collections.abc import Sequence

from core.provider import ModelMessage
from core.store import Lead


class InMemoryConversationStore:
    def __init__(self) -> None:
        self._sessions: defaultdict[str, list[ModelMessage]] = defaultdict(list)
        self._leads: dict[str, Lead] = {}

    async def load(self, session_id: str) -> tuple[ModelMessage, ...]:
        return tuple(self._sessions[session_id])

    async def append(self, session_id: str, messages: Sequence[ModelMessage]) -> None:
        self._sessions[session_id].extend(messages)

    async def get_lead(self, session_id: str) -> Lead | None:
        return self._leads.get(session_id)

    async def upsert_lead(self, session_id: str, lead: Lead) -> Lead:
        # Keyed by the Session, so a second call updates the Lead instead of adding one.
        self._leads[session_id] = lead
        return lead
