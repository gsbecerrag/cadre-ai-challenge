"""The Firestore `ConversationStore` — the one production implementation of the seam.

The API is stateless (ADR-0003): every Turn loads the Session and writes it back, so a Visitor
can refresh the page, and a second Cloud Run instance can serve the next Turn, and the
conversation is still there. That is the whole reason this exists next to the in-memory store,
which is correct for exactly one process.

Layout, per docs/architecture.md:

    sessions/{session_id}                 created_at, updated_at, turn_count, message_count
    sessions/{session_id}/messages/{seq}  sequence, role, content, tool fields, created_at

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

from core.logging import get_logger
from core.provider import MessageRole, ModelMessage, ToolCall

SESSIONS = "sessions"
MESSAGES = "messages"

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
    ) -> None:
        self._project = project
        self._collection = collection
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
        # One read to learn where this Turn's messages start. The alternative — ordering by a
        # server timestamp — cannot separate two messages written in the same batch.
        snapshot = await session.get()
        state = snapshot.to_dict() or {} if snapshot.exists else {}
        first = int(state.get("message_count", 0))
        turns = sum(1 for message in messages if message.role == "visitor")

        batch = client.batch()
        for offset, message in enumerate(messages):
            sequence = first + offset
            batch.set(
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
        batch.set(session, session_state, merge=True)
        await batch.commit()
        logger.info(
            "Session written",
            extra={"messages": len(messages), "message_count": first + len(messages)},
        )


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
