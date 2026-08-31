"""The Assistant's tool registry.

Four tools. The order here is the serialisation order in the prompt's cached prefix — append,
never insert — and `offer_live_handover` is last because it is the only one the model does not
always get: it appears when the Session's Lead becomes a Qualified Lead, so putting it at the
end means its arrival changes the tail of the cached prefix rather than the middle of it.
"""

from core.adapters.memory_notifier import InMemoryNotifier
from core.notifier import Notifier
from core.qualification import DEFAULT_QUALIFICATION_THRESHOLD
from core.store import ConversationStore
from core.tools.capture_lead import capture_lead_tool
from core.tools.escalate import ESCALATE_TOOL
from core.tools.offer_live_handover import offer_live_handover_tool
from core.tools.registry import Tool, ToolOutcome, ToolRegistry, ToolRun
from core.tools.show_walkthrough import SHOW_WALKTHROUGH_TOOL


def default_tools(
    store: ConversationStore,
    notifier: Notifier | None = None,
    *,
    qualification_threshold: int = DEFAULT_QUALIFICATION_THRESHOLD,
) -> ToolRegistry:
    """Every tool the Assistant may call.

    `capture_lead` and `offer_live_handover` write through the same `ConversationStore` the
    Turn's history goes to, so the Session, its Lead and its Handover Request are one database
    and one seam. The `Notifier` defaults to the in-memory one — a caller that has not wired a
    channel still gets a working offer, and the deployed Console hears about the request
    through the store write either way (see `core/adapters/firestore_notifier.py`).
    """
    return ToolRegistry(
        [
            ESCALATE_TOOL,
            SHOW_WALKTHROUGH_TOOL,
            capture_lead_tool(store, qualification_threshold=qualification_threshold),
            offer_live_handover_tool(store, notifier or InMemoryNotifier()),
        ]
    )


__all__ = [
    "ESCALATE_TOOL",
    "SHOW_WALKTHROUGH_TOOL",
    "Tool",
    "ToolOutcome",
    "ToolRegistry",
    "ToolRun",
    "capture_lead_tool",
    "default_tools",
    "offer_live_handover_tool",
]
