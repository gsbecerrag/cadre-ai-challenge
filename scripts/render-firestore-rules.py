#!/usr/bin/env python
"""Render the Strategist allowlist from `ADMIN_ALLOWED_EMAILS` into `firestore.rules`.

The Console enforces the allowlist twice — once in the API, once in Firestore's rules, because
the browser reads Leads live and a realtime listener never passes through the API (ADR-0010).
Two enforcement points that drift apart is the failure this script exists to prevent: the API
reads the environment variable at startup, and `make rules` writes the same value between the
markers in the rules file, so the committed rules always say what the deployment says.

Only the block between the markers is rewritten. The rules themselves stay a readable,
hand-edited file rather than a string inside a script.

    make rules            # rewrite firestore.rules from .env
    make deploy-rules     # firebase deploy --only firestore:rules,firestore:indexes
"""

import os
import sys
from pathlib import Path

from core.auth import parse_allowlist

RULES = Path(__file__).resolve().parent.parent / "firestore.rules"
BEGIN = "    // BEGIN allowlist"
END = "    // END allowlist"


def render(emails: frozenset[str]) -> str:
    """The `allowlist()` function the rules call, sorted so a re-render is a stable diff."""
    entries = ",\n".join(f"        '{email}'" for email in sorted(emails))
    return (
        f"{BEGIN} — rendered by `make rules` from ADMIN_ALLOWED_EMAILS. Do not edit by hand.\n"
        "    function allowlist() {\n"
        "      return [\n"
        f"{entries}\n"
        "      ];\n"
        "    }\n"
        f"{END}"
    )


def replace_block(rules: str, rendered: str) -> str:
    start = rules.index(BEGIN)
    end = rules.index(END) + len(END)
    return rules[:start] + rendered + rules[end:]


def main() -> int:
    allowlist = parse_allowlist(os.environ.get("ADMIN_ALLOWED_EMAILS", ""))
    if not allowlist:
        # Rendering an empty list would silently lock every Strategist out of the realtime
        # reads while the API still worked, which is the most confusing possible half-failure.
        sys.stderr.write(
            "ADMIN_ALLOWED_EMAILS is empty, so there is no allowlist to render. "
            "Set it in .env (see .env.example) — firestore.rules is unchanged.\n"
        )
        return 1
    RULES.write_text(replace_block(RULES.read_text(encoding="utf-8"), render(allowlist)))
    sys.stderr.write(f"firestore.rules: {len(allowlist)} allowlisted Strategist email(s).\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
