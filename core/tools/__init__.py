"""The Assistant's tool registry.

Three tools today; ticket 11 adds `offer_live_handover`. The order here is the serialisation
order in the prompt's cached prefix — append, never insert.
"""

from core.qualification import DEFAULT_QUALIFICATION_THRESHOLD
from core.store import ConversationStore
from core.tools.capture_lead import capture_lead_tool
from core.tools.escalate import ESCALATE_TOOL
from core.tools.registry import Tool, ToolOutcome, ToolRegistry, ToolRun
from core.tools.show_walkthrough import SHOW_WALKTHROUGH_TOOL


def default_tools(
    store: ConversationStore,
    *,
    qualification_threshold: int = DEFAULT_QUALIFICATION_THRESHOLD,
) -> ToolRegistry:
    """Every tool the Assistant may call. `capture_lead` writes the Lead through the same
    `ConversationStore` the Turn's history goes to, so both are one database and one seam."""
    return ToolRegistry(
        [
            ESCALATE_TOOL,
            SHOW_WALKTHROUGH_TOOL,
            capture_lead_tool(store, qualification_threshold=qualification_threshold),
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
]
