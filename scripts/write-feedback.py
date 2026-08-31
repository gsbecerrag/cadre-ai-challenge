#!/usr/bin/env python
"""Write a Session, a Turn and a Feedback document — the input the Triage Agent triggers on.

For the emulator flow in `functions/README.md`: the Firebase emulator emulates Firestore, so
the way to fire the trigger locally is to write the document a Visitor's thumb would have
written. Point it at the emulator and nothing here can reach the real project:

    FIRESTORE_EMULATOR_HOST=127.0.0.1:8080 uv run scripts/write-feedback.py --rating down

Everything it writes is obviously fake (constraint 5) and scoped to one Session id, so a
second run overwrites its own Session rather than adding to somebody's conversation.
"""

import argparse
import asyncio
import os

from core.adapters.firestore_store import FirestoreConversationStore
from core.provider import ModelMessage
from core.store import Feedback

SESSION_ID = "sess-emulator-triage"
TRACE_ID = "emulator0000trace0000feedback0001"

CONVERSATION = (
    ModelMessage(role="visitor", content="Do you have SOC 2?"),
    ModelMessage(
        role="assistant",
        content=(
            "I can't confirm Cadre's security certifications — they aren't published "
            "[not-published#certifications]. A strategist can answer that directly."
        ),
    ),
)
COMMENT = (
    "It just said it couldn't confirm anything — I needed the security basics for my vendor form."
)


async def write(rating: str, project: str) -> None:
    store = FirestoreConversationStore(project=project)
    await store.append(SESSION_ID, CONVERSATION, trace_id=TRACE_ID)
    await store.save_feedback(
        Feedback(
            session_id=SESSION_ID,
            trace_id=TRACE_ID,
            rating="down" if rating == "down" else "up",
            comment=COMMENT if rating == "down" else "",
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rating", choices=("up", "down"), default="down")
    parser.add_argument("--project", default=os.environ.get("GOOGLE_CLOUD_PROJECT", ""))
    arguments = parser.parse_args()
    if not os.environ.get("FIRESTORE_EMULATOR_HOST"):
        parser.error(
            "FIRESTORE_EMULATOR_HOST is not set. This writes fake Feedback; point it at the "
            "emulator, never at the deployed project."
        )
    asyncio.run(write(arguments.rating, arguments.project))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
