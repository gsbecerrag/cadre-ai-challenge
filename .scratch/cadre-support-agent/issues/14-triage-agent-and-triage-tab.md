# 14: Triage Agent on thumbs-down and the Console Triage tab

**What to build:** When a Visitor gives a thumbs-down, an independent Triage Agent — a Firebase Function (Python) triggered by the Feedback document's creation — reads the conversation (Refuse-Set-redacted) and the Trace metadata, makes one structured-output model call, and writes a Triage Report keyed by the Feedback id: category (knowledge gap, wrong escalation, hallucination, tone, personal data, bug, other), summary, evidence quotes, a suggested Knowledge Base addition, a suggested Eval Case, severity, and the model used. It posts the summary to Langfuse on the same Trace. A thumbs-up is a no-op; a redelivered event does not write twice. Strategists see reports newest-first in a Triage tab in the Console with a link to the Trace. The function shares the core package by copying it at deploy time; a deploy target and the local emulator flow are part of this ticket. Phase P4.

**Blocked by:** 10 (Strategist Console with Google sign-in, Availability, and Leads), 12 (Thumbs up/down becomes Feedback and a Langfuse score)

**Design reference:** [docs/design](../../../docs/design/README.md) — brief §3.3: the Triage tab (heading "Triage reports", subtitle "Written by the Triage Agent on every thumbs-down. Newest first."), report cards with the category chip (Knowledge gap on `#f2efe4`/`#996`, Wrong escalation on `#fdeaea`/`#db4545`; add chip styles for the other five categories), severity label, timestamp, "Open trace in Langfuse ↗", summary, italic evidence block on cream, and the dashed boxes "Suggested KB addition" / "Suggested eval case" (monospace).

**Status:** ready-for-agent

- [ ] The handler, invoked with a fake Firestore event for a thumbs-up, writes nothing; for a thumbs-down it writes a Triage Report with every field of the schema; invoked twice for the same Feedback id it writes once; covered at seam S3 with a fake Firestore client and the stub provider returning a structured-output fixture.
- [ ] The structured-output request uses a JSON schema the provider seam supports, and a malformed model response produces a report with category `other` and the raw summary rather than a crash; covered at S3.
- [ ] The Console Triage tab lists reports via a realtime listener with category, severity, summary, suggestions, and the Trace link; allowlist enforced as in ticket 10.
- [ ] The function deploys with `make deploy-functions` (core package copied in), and the emulator flow fires it locally; on the deployed app a real thumbs-down produces a report in the Console within a minute. Screenshots attached to the PR.
- [ ] If the Functions deploy is blocked after a bounded effort, the fallback (a background task in the API) is implemented behind the same handler and recorded in the ADR and plan.md's cut log.
- [ ] The Triage tab matches the design reference for all seven categories.
