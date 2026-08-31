"""The production `Notifier`: the Firestore write the store already made.

There is no second write here, and that is the decision rather than an omission. The Console
holds a realtime listener on `handover_requests` (ADR-0010 accepted the browser reading
Firestore directly, with the rules mirroring the allowlist), so the document
`ConversationStore.create_handover` writes is delivered to every open Console within a moment
of being written — which is what raises the browser notification and plays the sound.

Anything this class wrote would therefore be a copy of a fact the Console already has, kept in
step by hand. So it logs, and the seam stays where a Phase 2 channel — Slack, email — plugs in
without the Turn or the tool knowing about it.

No Firestore import: the write belongs to the store adapter, which is the only module that
knows Firestore exists (constraint 7).
"""

from core.handover import HandoverRequest
from core.logging import get_logger

logger = get_logger("notifier.firestore")


class FirestoreNotifier:
    async def handover_created(self, request: HandoverRequest) -> None:
        logger.info(
            "Hand-over offered; the Console's listener has the request",
            extra={"request_id": request.id, "qualification_score": request.lead.score},
        )
