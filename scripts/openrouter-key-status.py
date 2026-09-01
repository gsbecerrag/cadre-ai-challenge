#!/usr/bin/env python3
"""Report whether an OpenRouter key is alive and how much credit it has left.

The key is read from stdin — never from an argument — so it appears in no shell history and
no process list. Prints one line per fact OpenRouter reports about the key (label, usage,
limit, what remains, when the limit resets, when the key expires) and exits 0 when the key is
accepted, 1 when OpenRouter rejects it, 2 when nothing was given. The Makefile's
`check-openrouter-key` pipes the deployed secret in; `rotate-openrouter-key` pipes the
candidate key in before writing it anywhere.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime

KEY_ENDPOINT = "https://openrouter.ai/api/v1/key"


def describe_expiry(expires_at: str | None) -> str:
    """OpenRouter's ISO timestamp as a date and a countdown, or "never" when there is none."""
    if not expires_at:
        return "never"
    expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    remaining = expiry - datetime.now(UTC)
    days = remaining.days
    when = expiry.strftime("%Y-%m-%d %H:%M UTC")
    if remaining.total_seconds() <= 0:
        return f"{when} — EXPIRED"
    return f"{when} — in {days} day{'s' if days != 1 else ''}"


def say(line: str) -> None:
    """A report for the person at the terminal, not a log line — so stdout, not core.logging."""
    sys.stdout.write(line + "\n")


def main() -> int:
    key = sys.stdin.read().strip()
    if not key:
        sys.stderr.write("No key on stdin; nothing checked.\n")
        return 2
    request = urllib.request.Request(KEY_ENDPOINT, headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.load(response).get("data", {})
    except urllib.error.HTTPError as error:
        sys.stderr.write(f"OpenRouter rejected the key: HTTP {error.code}\n")
        return 1
    except (urllib.error.URLError, TimeoutError) as error:
        sys.stderr.write(f"Could not reach OpenRouter: {error}\n")
        return 1
    limit = data.get("limit")
    remaining = data.get("limit_remaining")
    say(f"label:            {data.get('label', '?')}")
    say(f"usage so far:     ${float(data.get('usage', 0) or 0):.2f}")
    say(f"limit:            {'none' if limit is None else f'${float(limit):.2f}'}")
    say(f"remaining:        {'unlimited' if remaining is None else f'${float(remaining):.2f}'}")
    say(f"free tier:        {'yes' if data.get('is_free_tier') else 'no'}")
    say(f"limit resets:     {data.get('limit_reset') or 'never (a lifetime cap)'}")
    say(f"expires:          {describe_expiry(data.get('expires_at'))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
