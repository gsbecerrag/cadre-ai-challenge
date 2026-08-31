"""The `Notifier` seam: telling Cadre that a Hand-over is waiting.

One production implementation, and it is a strange one on purpose: the Firestore write *is* the
notification (the spec's Hand-over section). The Console subscribes to `handover_requests` with
a realtime listener, so the document the store already wrote is what raises the browser
notification and the sound — a second write, a queue or a webhook would be a second thing to
keep in step with the first for no extra information.

The seam still exists, and not only for the test double. It is the one place a later channel
plugs in — Slack, email, SMS are Phase 2 — and it is where "a Qualified Lead is offered a
Hand-over exactly once" can be observed in a test without reaching into the store.
"""

from typing import Protocol

from core.handover import HandoverRequest


class Notifier(Protocol):
    """Announces a Handover Request to the people who can pick it up."""

    async def handover_created(self, request: HandoverRequest) -> None:
        """A Hand-over has been offered. Called once per Handover Request, after it is stored,
        so whatever a channel sends describes a request that exists."""
        ...
