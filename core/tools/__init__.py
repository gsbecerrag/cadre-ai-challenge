"""The Assistant's tool registry.

One tool today. Ticket 08 adds `show_walkthrough`, 09 `capture_lead`, 11 `offer_live_handover`.
The order here is the serialisation order in the prompt's cached prefix — append, never insert.
"""

from core.tools.escalate import ESCALATE_TOOL
from core.tools.registry import Tool, ToolOutcome, ToolRegistry


def default_tools() -> ToolRegistry:
    return ToolRegistry([ESCALATE_TOOL])


__all__ = ["ESCALATE_TOOL", "Tool", "ToolOutcome", "ToolRegistry", "default_tools"]
