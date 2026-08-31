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
    handover_requests/{request_id}        created_at, updated_at, session ref, session_id,
                                          state, mode, prompt, trace_id, lead snapshot
    strategists/{uid}                     online, email, name, updated_at

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
from google.cloud.firestore_v1.base_query import FieldFilter

from core.auth import StrategistIdentity
from core.handover import HandoverMode, HandoverRequest, HandoverState, LeadSnapshot
from core.logging import get_logger
from core.provider import MessageRole, ModelMessage, ToolCall
from core.store import (
    CONTACT_DETAIL_NAMES,
    DEFAULT_HANDOVER_PAGE,
    DEFAULT_LEAD_PAGE,
    Lead,
)
from core.video import Room

SESSIONS = "sessions"
MESSAGES = "messages"
# A top-level collection, keyed by the Session id: one Lead per Session, and a Console that
# lists Leads without walking every Session first (docs/architecture.md §5).
LEADS = "leads"
# Handover Requests, keyed by the request id. A top-level collection because it is the
# Console's work list: a Strategist opens one screen and reads every waiting request, and the
# realtime listener that raises their notification is a listener on this one collection.
HANDOVERS = "handover_requests"

# Presence, keyed by the Strategist's Firebase uid: one document per Strategist, which is what
# lets a Console listener render who is online and lets `firestore.rules` say "you may write
# your own and nobody else's" in one line.
STRATEGISTS = "strategists"

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
        handovers_collection: str = HANDOVERS,
        strategists_collection: str = STRATEGISTS,
    ) -> None:
        self._project = project
        self._collection = collection
        self._leads_collection = leads_collection
        self._handovers_collection = handovers_collection
        self._strategists_collection = strategists_collection
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

    async def list_leads(self, limit: int = DEFAULT_LEAD_PAGE) -> tuple[Lead, ...]:
        """The Console's page of Leads, most recently updated first.

        `updated_at` and not `created_at`: a Lead the Assistant just learned a phone number
        for is newer work than one it has not touched since this morning. Ordering on one
        field needs no composite index, which is why `firestore.indexes.json` is empty.
        """
        query = (
            self._connect()
            .collection(self._leads_collection)
            .order_by("updated_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
        )
        return tuple(
            [_lead(document.id, document.to_dict() or {}) async for document in query.stream()]
        )

    async def set_availability(self, strategist: StrategistIdentity, online: bool) -> None:
        """Write this Strategist's presence document.

        `merge=True` and keyed by the uid: signing in on a second device moves the same
        presence rather than adding a second Strategist to the Availability count. The email
        and name travel with it because the Console renders who is online, and a uid is not a
        person to a human reading the list.
        """
        await (
            self._connect()
            .collection(self._strategists_collection)
            .document(strategist.uid)
            .set(
                {
                    "online": online,
                    "email": strategist.email,
                    "name": strategist.name,
                    "updated_at": firestore.SERVER_TIMESTAMP,
                },
                merge=True,
            )
        )

    async def get_availability(self, uid: str) -> bool:
        document = (
            await self._connect().collection(self._strategists_collection).document(uid).get()
        )
        return bool((document.to_dict() or {}).get("online", False)) if document.exists else False

    async def any_strategist_online(self) -> bool:
        """Whether anyone is online, asked as cheaply as Firestore allows.

        `limit(1)`: the answer is a boolean, so reading every Strategist to count them would
        be a document charge per Strategist per Turn that reaches this question.
        """
        query = (
            self._connect()
            .collection(self._strategists_collection)
            .where(filter=FieldFilter("online", "==", True))
            .limit(1)
        )
        return any([True async for _ in query.stream()])

    async def create_handover(self, request: HandoverRequest) -> HandoverRequest:
        """Write a newly offered Handover Request.

        This write *is* the notification (see core/adapters/firestore_notifier.py): every open
        Console holds a listener on this collection, so the document arriving is what raises
        the browser notification and plays the sound. Nothing else has to be sent.
        """
        client = self._connect()
        reference = client.collection(self._handovers_collection).document(request.id)
        document = _handover_document(request)
        document["session"] = client.collection(self._collection).document(request.session_id)
        document["created_at"] = firestore.SERVER_TIMESTAMP
        await reference.set(document)
        # Ids and counts only: the request carries the Visitor's Contact Details.
        logger.info(
            "Handover Request written",
            extra={"request_id": request.id, "qualification_score": request.lead.score},
        )
        return await self._read_handover(request.id) or request

    async def get_handover(self, request_id: str) -> HandoverRequest | None:
        return await self._read_handover(request_id)

    async def handover_for_session(self, session_id: str) -> HandoverRequest | None:
        """The Session's request, if it has one.

        Filtered on `session_id` and limited to one: this is asked on the provider call that
        decides whether the Assistant may be given the offer tool, so it has to be one cheap
        read rather than a scan of the collection.
        """
        query = (
            self._connect()
            .collection(self._handovers_collection)
            .where(filter=FieldFilter("session_id", "==", session_id))
            .limit(1)
        )
        async for document in query.stream():
            return _handover(document.id, document.to_dict() or {})
        return None

    async def update_handover(
        self,
        request_id: str,
        state: HandoverState,
        mode: HandoverMode | None = None,
        lead: LeadSnapshot | None = None,
        *,
        room: Room | None = None,
        strategist_name: str | None = None,
        expected_state: HandoverState | None = None,
    ) -> HandoverRequest:
        """Write a transition the caller has already validated against the state machine.

        `merge=True` and a field-by-field update, so a field this build does not know about is
        kept rather than dropped, and an argument the caller did not decide — the `mode`, the
        Daily room, who claimed it — is left exactly as it was.

        One write per move, including the two that carry something with them: the acceptance
        stores the room alongside `mode: video`, and the Console's Join stores the Strategist's
        name alongside `in_call`. The Console's realtime listener reads this document, so a
        move written in two parts would be a queue that flickered through a state nobody was
        ever in.

        `expected_state` turns the write into a compare-and-set, and needs a transaction rather
        than a precondition on the set: Firestore has no "write if this field equals that", so
        the state is re-read inside the transaction the write commits in.
        """
        document: dict[str, Any] = {"state": state, "updated_at": firestore.SERVER_TIMESTAMP}
        if mode is not None:
            document["mode"] = mode
        if lead is not None:
            document["lead"] = _lead_snapshot_document(lead)
        if room is not None:
            document["room_url"] = room.url
            document["room_expires_at"] = room.expires_at
        if strategist_name is not None:
            document["strategist_name"] = strategist_name
        client = self._connect()
        reference = client.collection(self._handovers_collection).document(request_id)
        if expected_state is None:
            await reference.set(document, merge=True)
        else:
            await _set_if_still_in(client.transaction(), reference, document, expected_state)
        logger.info(
            "Handover Request updated", extra={"request_id": request_id, "handover_state": state}
        )
        updated = await self._read_handover(request_id)
        if updated is None:
            raise KeyError(f"There is no Handover Request {request_id!r} to update.")
        return updated

    async def list_handovers(
        self, mode: HandoverMode | None = None, limit: int = DEFAULT_HANDOVER_PAGE
    ) -> tuple[HandoverRequest, ...]:
        """The Console's page, newest first.

        Ordered on `created_at` — when the Visitor asked — rather than `updated_at`: a queue
        that reshuffled itself every time a Strategist changed a state would move the card
        under their cursor.

        The `mode` filter is an equality on one field plus an order on another, which is the
        one shape Firestore's single-field indexes cannot serve — it is the composite index in
        `firestore.indexes.json`, deployed by `make deploy-rules`. Verified against the real
        project rather than assumed: the first run of that check failed with
        `FailedPrecondition: the query requires an index`.
        """
        collection = self._connect().collection(self._handovers_collection)
        query = collection.order_by("created_at", direction=firestore.Query.DESCENDING)
        if mode is not None:
            query = collection.where(filter=FieldFilter("mode", "==", mode)).order_by(
                "created_at", direction=firestore.Query.DESCENDING
            )
        return tuple(
            [
                _handover(document.id, document.to_dict() or {})
                async for document in query.limit(limit).stream()
            ]
        )

    async def _read_handover(self, request_id: str) -> HandoverRequest | None:
        document = (
            await self._connect().collection(self._handovers_collection).document(request_id).get()
        )
        if not document.exists:
            return None
        return _handover(document.id, document.to_dict() or {})


@firestore.async_transactional
async def _set_if_still_in(
    transaction: AsyncTransaction,
    reference: AsyncDocumentReference,
    document: dict[str, Any],
    expected_state: HandoverState,
) -> None:
    """Write these fields only while the request is still in `expected_state`.

    The read is inside the transaction, so a write that lands between it and the commit aborts
    this one rather than being overwritten by it. A request that has moved on is left exactly
    as it is: the caller re-reads and reports what it finds.
    """
    snapshot = await reference.get(transaction=transaction)
    if not snapshot.exists or (snapshot.to_dict() or {}).get("state") != expected_state:
        return
    transaction.set(reference, document, merge=True)


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


def _handover_document(request: HandoverRequest) -> dict[str, Any]:
    """One Handover Request as a Firestore document.

    The Lead is a nested snapshot rather than a reference, so the Console's queue is one read
    per screen; `session` is a reference as well, so a Strategist can open the conversation
    without either document duplicating the other.
    """
    return {
        "session_id": request.session_id,
        "state": request.state,
        "mode": request.mode,
        "prompt": request.prompt,
        "trace_id": request.trace_id,
        "lead": _lead_snapshot_document(request.lead),
        "room_url": request.room_url,
        "strategist_name": request.strategist_name,
        "updated_at": firestore.SERVER_TIMESTAMP,
    }


def _lead_snapshot_document(lead: LeadSnapshot) -> dict[str, Any]:
    document: dict[str, Any] = {
        "signals": dict(lead.signals),
        "score": lead.score,
        "qualified": lead.qualified,
    }
    for name in CONTACT_DETAIL_NAMES:
        document[name] = str(getattr(lead, name, "") or "")
    return document


def _handover(request_id: str, document: Mapping[str, Any]) -> HandoverRequest:
    state: HandoverState = document.get("state", "offered")
    mode: HandoverMode | None = document.get("mode") or None
    return HandoverRequest(
        id=request_id,
        session_id=str(document.get("session_id") or ""),
        state=state,
        mode=mode,
        prompt=str(document.get("prompt") or ""),
        lead=_lead_snapshot(document.get("lead") or {}),
        created_at=document.get("created_at"),
        updated_at=document.get("updated_at"),
        trace_id=document.get("trace_id"),
        room_url=str(document.get("room_url") or ""),
        room_expires_at=document.get("room_expires_at"),
        strategist_name=str(document.get("strategist_name") or ""),
    )


def _lead_snapshot(document: Mapping[str, Any]) -> LeadSnapshot:
    signals = document.get("signals") or {}
    return LeadSnapshot(
        signals={str(name): str(value) for name, value in signals.items()},
        score=int(document.get("score", 0)),
        qualified=bool(document.get("qualified", False)),
        **{name: str(document.get(name) or "") for name in CONTACT_DETAIL_NAMES},
    )
