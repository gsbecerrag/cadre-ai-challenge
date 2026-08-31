"""The in-memory `ConversationStore` — the test implementation, and `make dev` without GCP.

Process-local by definition: it is correct for one process and wrong for a Cloud Run service
that scales past one instance, which is exactly why ticket 03 puts Firestore behind the same
seam.
"""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime

from core.auth import StrategistIdentity
from core.handover import HandoverMode, HandoverRequest, HandoverState, LeadSnapshot
from core.provider import ModelMessage
from core.store import DEFAULT_HANDOVER_PAGE, DEFAULT_LEAD_PAGE, Feedback, Lead


class InMemoryConversationStore:
    def __init__(self) -> None:
        self._sessions: defaultdict[str, list[ModelMessage]] = defaultdict(list)
        self._leads: dict[str, Lead] = {}
        self._online: set[str] = set()
        # Which Traces each Session produced, and the Feedback left on them, keyed by the
        # Feedback's own id. In Firestore the first of these is a field on the stored messages
        # and the second a collection; in one process a set and a dict say the same thing.
        self._traces: dict[str, set[str]] = {}
        self._feedback: dict[str, Feedback] = {}
        # Insertion order is "oldest first", which `list_handovers` reverses — the same trick
        # `list_leads` uses, and what Firestore's `created_at` ordering gives it.
        self._handovers: dict[str, HandoverRequest] = {}

    async def load(self, session_id: str) -> tuple[ModelMessage, ...]:
        return tuple(self._sessions[session_id])

    async def append(
        self, session_id: str, messages: Sequence[ModelMessage], trace_id: str | None = None
    ) -> None:
        self._sessions[session_id].extend(messages)
        if trace_id:
            self._traces.setdefault(session_id, set()).add(trace_id)

    async def trace_belongs_to(self, session_id: str, trace_id: str) -> bool:
        return trace_id in self._traces.get(session_id, frozenset())

    async def get_feedback(self, session_id: str, trace_id: str) -> Feedback | None:
        stored = self._feedback.get(trace_id)
        return stored if stored is not None and stored.session_id == session_id else None

    async def save_feedback(self, feedback: Feedback) -> Feedback:
        self._feedback[feedback.id] = feedback
        return feedback

    async def get_lead(self, session_id: str) -> Lead | None:
        return self._leads.get(session_id)

    async def upsert_lead(self, session_id: str, lead: Lead) -> Lead:
        # Keyed by the Session, so a second call updates the Lead instead of adding one, and
        # re-inserted rather than assigned in place: `list_leads` reads insertion order as
        # "least recently written first", which is what Firestore's `updated_at` gives it.
        self._leads.pop(session_id, None)
        self._leads[session_id] = lead
        return lead

    async def list_leads(self, limit: int = DEFAULT_LEAD_PAGE) -> tuple[Lead, ...]:
        return tuple(reversed(list(self._leads.values())))[:limit]

    async def set_availability(self, strategist: StrategistIdentity, online: bool) -> None:
        # A set, not a map: in memory there is no presence document to keep, only the one
        # fact anybody asks about. The Firestore adapter keeps the email and the name too,
        # because a Console listener there renders who is online.
        if online:
            self._online.add(strategist.uid)
        else:
            self._online.discard(strategist.uid)

    async def get_availability(self, uid: str) -> bool:
        return uid in self._online

    async def any_strategist_online(self) -> bool:
        return bool(self._online)

    async def create_handover(self, request: HandoverRequest) -> HandoverRequest:
        now = datetime.now(tz=UTC)
        stored = replace(request, created_at=now, updated_at=now)
        self._handovers[stored.id] = stored
        return stored

    async def get_handover(self, request_id: str) -> HandoverRequest | None:
        return self._handovers.get(request_id)

    async def handover_for_session(self, session_id: str) -> HandoverRequest | None:
        for request in reversed(list(self._handovers.values())):
            if request.session_id == session_id:
                return request
        return None

    async def update_handover(
        self,
        request_id: str,
        state: HandoverState,
        mode: HandoverMode | None = None,
        lead: LeadSnapshot | None = None,
    ) -> HandoverRequest:
        request = self._handovers[request_id]
        updated = replace(
            request,
            state=state,
            mode=mode if mode is not None else request.mode,
            lead=lead if lead is not None else request.lead,
            updated_at=datetime.now(tz=UTC),
        )
        self._handovers[request_id] = updated
        return updated

    async def list_handovers(
        self, mode: HandoverMode | None = None, limit: int = DEFAULT_HANDOVER_PAGE
    ) -> tuple[HandoverRequest, ...]:
        newest_first = reversed(list(self._handovers.values()))
        return tuple(request for request in newest_first if mode is None or request.mode == mode)[
            :limit
        ]
