# 14: Triage Agent on thumbs-down and the Console Triage tab

**What to build:** When a Visitor gives a thumbs-down, an independent Triage Agent — a Firebase Function (Python) triggered by the Feedback document's creation — reads the conversation (Refuse-Set-redacted) and the Trace metadata, makes one structured-output model call, and writes a Triage Report keyed by the Feedback id: category (knowledge gap, wrong escalation, hallucination, tone, personal data, bug, other), summary, evidence quotes, a suggested Knowledge Base addition, a suggested Eval Case, severity, and the model used. It posts the summary to Langfuse on the same Trace. A thumbs-up is a no-op; a redelivered event does not write twice. Strategists see reports newest-first in a Triage tab in the Console with a link to the Trace. The function shares the core package by copying it at deploy time; a deploy target and the local emulator flow are part of this ticket. Phase P4.

**Blocked by:** 10 (Strategist Console with Google sign-in, Availability, and Leads), 12 (Thumbs up/down becomes Feedback and a Langfuse score)

**Design reference:** [docs/design](../../../docs/design/README.md) — brief §3.3: the Triage tab (heading "Triage reports", subtitle "Written by the Triage Agent on every thumbs-down. Newest first."), report cards with the category chip (Knowledge gap on `#f2efe4`/`#996`, Wrong escalation on `#fdeaea`/`#db4545`; add chip styles for the other five categories), severity label, timestamp, "Open trace in Langfuse ↗", summary, italic evidence block on cream, and the dashed boxes "Suggested KB addition" / "Suggested eval case" (monospace).

**Status:** done

- [x] The handler, invoked with a fake Firestore event for a thumbs-up, writes nothing; for a thumbs-down it writes a Triage Report with every field of the schema; invoked twice for the same Feedback id it writes once; covered at seam S3 with a fake Firestore client and the stub provider returning a structured-output fixture.
- [x] The structured-output request uses a JSON schema the provider seam supports, and a malformed model response produces a report with category `other` and the raw summary rather than a crash; covered at S3.
- [x] The Console Triage tab lists reports via a realtime listener with category, severity, summary, suggestions, and the Trace link; allowlist enforced as in ticket 10.
- [x] The function deploys with `make deploy-functions` (core package copied in), and the emulator flow fires it locally; on the deployed app a real thumbs-down produces a report in the Console within a minute. Screenshots attached to the PR.
- [x] If the Functions deploy is blocked after a bounded effort, the fallback (a background task in the API) is implemented behind the same handler and recorded in the ADR and plan.md's cut log.
- [x] The Triage tab matches the design reference for all seven categories.

## Comments

- Delivered in [PR #26](https://github.com/gsbecerrag/cadre-ai-challenge/pull/26). Reviewer: one Important (non-existent function-shaped secret ids) and two minors fixed in round 1; scoped re-review: all addressed, no new breakage.
- Ruling: the handler is seam-pure in `core/triage.py` (S3 with fakes); the report is keyed by the Feedback id so redelivery overwrites; malformed output degrades to `other`; the triage score has its own name so it can never overwrite the Visitor's thumb; the trigger is document WRITES with the rating-became-down guard (ADR-0005 amended).
- Parked: secret-copy rotation drift; `functions/main.py` outside mypy (watched via the two log lines on the first deploy); the ADR summary line + the spec's stale creation wording → ticket 19; the emulator run (host crashes) — superseded by the deployed check.
- The deployed check (a real thumbs-down → a Triage Report in the Console within a minute; screenshots) is recorded here after the merge + make deploy-functions.
- Deployed-app check recorded: [docs/transcripts/2026-08-31-deployed-checks-14-15-20.md](../../../docs/transcripts/2026-08-31-deployed-checks-14-15-20.md) — revision `e619c71`; the Triage Function is live.
