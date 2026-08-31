"""The Assistant's tool registry.

Two tools today. Ticket 09 adds `capture_lead`, 11 `offer_live_handover`. The order here is the
serialisation order in the prompt's cached prefix — append, never insert.
"""

from core.tools.escalate import ESCALATE_TOOL
from core.tools.registry import Tool, ToolOutcome, ToolRegistry
from core.tools.show_walkthrough import SHOW_WALKTHROUGH_TOOL


def default_tools() -> ToolRegistry:
    return ToolRegistry([ESCALATE_TOOL, SHOW_WALKTHROUGH_TOOL])


__all__ = [
    "ESCALATE_TOOL",
    "SHOW_WALKTHROUGH_TOOL",
    "Tool",
    "ToolOutcome",
    "ToolRegistry",
    "default_tools",
]
