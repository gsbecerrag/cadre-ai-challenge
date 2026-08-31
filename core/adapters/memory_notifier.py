"""The in-memory `Notifier` — the test implementation, and `make dev` without a Console open.

It keeps what it was told, which is what lets an HTTP test assert the thing the product
promises ("a Qualified Lead is offered a Hand-over exactly once") at the place a Strategist
would have heard about it, rather than by counting rows in the store.
"""

from core.handover import HandoverRequest
from core.logging import get_logger

logger = get_logger("notifier")


class InMemoryNotifier:
    def __init__(self) -> None:
        self.created: list[HandoverRequest] = []

    async def handover_created(self, request: HandoverRequest) -> None:
        self.created.append(request)
        # Ids and counts only: the request carries the Visitor's Contact Details, and a log
        # line is not the place for them (constraint 8).
        logger.info("Hand-over offered", extra={"request_id": request.id})
