"""Frame a chat event as Server-Sent Events.

A pure function, because the framing is the wire contract: an unescaped newline in a delta
would end the frame early and the browser would silently drop the rest of the answer. JSON
encoding is what makes that impossible, so the payload is always JSON, even when it is one
string.
"""

import json

from core.events import ChatEvent

SSE_MEDIA_TYPE = "text/event-stream"

# `no-store` keeps a proxy from replaying a Turn; `x-accel-buffering: no` stops an nginx-shaped
# proxy from holding the deltas back until the Turn ends, which would defeat streaming.
SSE_HEADERS = {
    "cache-control": "no-store",
    "x-accel-buffering": "no",
}


def format_sse_event(event: ChatEvent) -> str:
    payload = json.dumps(event.data, separators=(",", ":"), ensure_ascii=False)
    return f"event: {event.name}\ndata: {payload}\n\n"
