"""The Firestore `ConversationStore` — the one production implementation of the seam.

The API is stateless (ADR-0003): every Turn loads the Session and writes it back, so a Visitor
can refresh the page, and a second Cloud Run instance can serve the next Turn, and the
conversation is still there. That is the whole reason this exists next to the in-memory store,
which is correct for exactly one process.

Layout, per docs/architecture.md:

    sessions/{session_id}                 created_at, updated_at, turn_count, message_count
    sessions/{session_id}/messages/{seq}  sequence, role, content, tool fields, created_at
    leads/{session_id}                    created_at, updated_at, session ref, Contact Details,
                                          signals, score, qualified

The document id of a message is its zero-padded sequence, and `sequence` is written as a field
as well, because ordering is the one thing this store must never get wrong: messages out of
order are a different conversation. Firestore's own document ids are random, and a server
timestamp is not unique enough to order two messages written in the same batch — so the
sequence is ours, taken from the message count the Session document already carries.

The Firestore SDK is imported here and nowhere else (constraint 7).
"""

import json
from collections.abc import Mapping, Sequence
from typing import Any

from google.cloud import firestore
from google.cloud.firestore_v1.async_document import AsyncDocumentReference
from google.cloud.firestore_v1.async_transaction import AsyncTransaction

from core.logging import get_logger
from core.provider import MessageRole, ModelMessage, ToolCall
from core.store import CONTACT_DETAIL_NAMES, Lead

SESSIONS = "sessions"
MESSAGES = "messages"
# A top-level collection, keyed by the Session id: one Lead per Session, and a Console that
# lists Leads without walking every Session first (docs/architecture.md §5).
LEADS = "leads"

# Wide enough that a Session hits its Turn cap long before the padding runs out, and fixed, so
# the document ids of one Session sort the way the sequence does.
SEQUENCE_WIDTH = 6

logger = get_logger("firestore")


class FirestoreConversationStore:
    """One Session's history, as a document and its `messages` subcollection."""

    def __init__(
        self,
        *,
        project: str = "",
        client: firestore.AsyncClient | None = None,
        collection: str = SESSIONS,
        leads_collection: str = LEADS,
    ) -> None:
        self._project = project
        self._collection = collection
        self._leads_collection = leads_collection
        self._client = client

    def _connect(self) -> firestore.AsyncClient:
        """Open the client on first use.

        Not in the constructor: the composition root builds this before the event loop is
        running, and the async client's gRPC channel belongs to the loop that will serve the
        requests. Credentials are Application Default Credentials — the developer's on a
        laptop, the runtime service account's on Cloud Run.
        """
        if self._client is None:
            self._client = (
                firestore.AsyncClient(project=self._project)
                if self._project
                else firestore.AsyncClient()
            )
        return self._client

    async def load(self, session_id: str) -> tuple[ModelMessage, ...]:
        session = self._connect().collection(self._collection).document(session_id)
        stored = session.collection(MESSAGES).order_by("sequence")
        return tuple([_message(document.to_dict() or {}) async for document in stored.stream()])

    async def append(self, session_id: str, messages: Sequence[ModelMessage]) -> None:
        if not messages:
            return
        client = self._connect()
        session = client.collection(self._collection).document(session_id)
        # In a transaction, because the sequence a message is written under is derived from
        # the count this read returns. Two Turns racing on one Session — two tabs, a
        # double-submit, two Cloud Run instances — would otherwise read the same count, write
        # the same document ids, and the later commit would erase the earlier Turn.
        await _append_in_sequence(client.transaction(), session, messages)
        logger.info("Session written", extra={"messages": len(messages)})

    async def get_lead(self, session_id: str) -> Lead | None:
        document = (
            await self._connect().collection(self._leads_collection).document(session_id).get()
        )
        if not document.exists:
            return None
        return _lead(session_id, document.to_dict() or {})

    async def upsert_lead(self, session_id: str, lead: Lead) -> Lead:
        client = self._connect()
        reference = client.collection(self._leads_collection).document(session_id)
        document = _lead_document(lead, client.collection(self._collection).document(session_id))
        # Read first, so `created_at` records when the Visitor first identified themselves
        # rather than the last time they mentioned anything. `merge=True` for the same reason:
        # a field this build does not know about is kept, not dropped.
        snapshot = await reference.get()
        if not snapshot.exists:
            document["created_at"] = firestore.SERVER_TIMESTAMP
        await reference.set(document, merge=True)
        # Counts only: the Contact Details on the Lead are raw, and a log line is not the place
        # for them (constraint 8).
        logger.info(
            "Lead written",
            extra={"qualification_score": lead.score, "qualified": lead.qualified},
        )
        return lead


@firestore.async_transactional
async def _append_in_sequence(
    transaction: AsyncTransaction,
    session: AsyncDocumentReference,
    messages: Sequence[ModelMessage],
) -> None:
    """Allocate this Turn's sequence numbers and write its messages, atomically.

    Every read comes before every write, which is what Firestore requires of a transaction —
    and the read is what the writes are derived from, which is why this is one.
    """
    snapshot = await session.get(transaction=transaction)
    state = snapshot.to_dict() or {} if snapshot.exists else {}
    first = int(state.get("message_count", 0))
    turns = sum(1 for message in messages if message.role == "visitor")

    for offset, message in enumerate(messages):
        sequence = first + offset
        transaction.set(
            session.collection(MESSAGES).document(f"{sequence:0{SEQUENCE_WIDTH}d}"),
            _document(message, sequence),
        )
    session_state: dict[str, Any] = {
        "updated_at": firestore.SERVER_TIMESTAMP,
        "message_count": first + len(messages),
        "turn_count": int(state.get("turn_count", 0)) + turns,
    }
    if not snapshot.exists:
        session_state["created_at"] = firestore.SERVER_TIMESTAMP
    transaction.set(session, session_state, merge=True)


def _document(message: ModelMessage, sequence: int) -> dict[str, Any]:
    """One message as a Firestore document. The roles are ours (`visitor`), not the wire's."""
    document: dict[str, Any] = {
        "sequence": sequence,
        "role": message.role,
        "content": message.content,
        "created_at": firestore.SERVER_TIMESTAMP,
    }
    if message.tool_calls:
        document["tool_calls"] = [
            {"id": call.id, "name": call.name, "arguments": json.dumps(dict(call.arguments))}
            for call in message.tool_calls
        ]
    if message.tool_call_id:
        document["tool_call_id"] = message.tool_call_id
    return document


def _message(document: Mapping[str, Any]) -> ModelMessage:
    role: MessageRole = document.get("role", "visitor")
    return ModelMessage(
        role=role,
        content=document.get("content", ""),
        tool_calls=tuple(_tool_call(call) for call in document.get("tool_calls", [])),
        tool_call_id=document.get("tool_call_id"),
    )


def _tool_call(stored: Mapping[str, Any]) -> ToolCall:
    written = stored.get("arguments") or "{}"
    try:
        arguments = json.loads(written)
    except json.JSONDecodeError:
        arguments = {}
    return ToolCall(
        id=stored.get("id", ""),
        name=stored.get("name", ""),
        arguments=arguments if isinstance(arguments, dict) else {},
    )


def _lead_document(lead: Lead, session: AsyncDocumentReference) -> dict[str, Any]:
    """One Lead as a Firestore document.

    The Contact Details are written raw and deliberately so (ADR-0006): the Refuse Set never
    reaches storage, and these are the opposite — the typed fields the product exists to
    collect, and the only way a Strategist reaches the Visitor back. `session` is a reference
    rather than a copy of the conversation, so the Console can open the Turn history from the
    Lead without either document duplicating the other.
    """
    document: dict[str, Any] = {
        "session": session,
        "session_id": lead.session_id,
        "signals": dict(lead.signals),
        "score": lead.score,
        "qualified": lead.qualified,
        "updated_at": firestore.SERVER_TIMESTAMP,
    }
    for name in CONTACT_DETAIL_NAMES:
        document[name] = str(getattr(lead, name, "") or "")
    return document


def _lead(session_id: str, document: Mapping[str, Any]) -> Lead:
    signals = document.get("signals") or {}
    return Lead(
        session_id=str(document.get("session_id") or session_id),
        signals={str(name): str(value) for name, value in signals.items()},
        score=int(document.get("score", 0)),
        qualified=bool(document.get("qualified", False)),
        **{name: str(document.get(name) or "") for name in CONTACT_DETAIL_NAMES},
    )
