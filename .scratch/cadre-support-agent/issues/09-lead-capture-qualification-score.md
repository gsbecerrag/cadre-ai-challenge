# 09: Lead capture with a Qualification Score computed in code

**What to build:** A Visitor shares their name, work email, company, phone, and role naturally during the conversation; the Assistant acknowledges without a lecture and a Lead is created for the Session with the five Qualification Signals it has learned (industry fit, company size or role, a concrete initiative or pain, a timeline or budget, explicit intent) and a Qualification Score computed in code as the count of signals present. Later details update the same Lead. The model never assigns the score; the threshold comes from configuration (default three). The system prompt gains qualification guidance: collect signals conversationally, never interrogate, call the tool as soon as any Contact Detail appears. Phase P2.

**Blocked by:** 03 (Real Grounded Answers on the public URL)

**Design reference:** [docs/design](../../../docs/design/README.md) — none directly: the design captures details through a "Your details" form card, which ticket 11 builds on top of this ticket's Lead upsert; this ticket implements the conversational `capture_lead` path from the spec. Ruling: the five Qualification Signals are the spec's (industry fit, company size or role, concrete initiative or pain, timeline or budget, explicit intent); the design's labels are superseded — see the rulings table.

**Status:** done

- [x] The score function returns the count of present signals (0–5) and the threshold comparison; covered at seam S2 with all boundary cases.
- [x] A Turn in which the provider calls `capture_lead` creates a Lead bound to the Session with the raw Contact Details, the signals, and the computed score; a second call updates the same Lead rather than creating another; covered at seam S1 with the in-memory store.
- [x] Contact Details on the Lead are stored raw (not tokenised) while the message history still passes through the `refuse` profile; covered at S1.
- [x] The Firestore store persists Leads under their own collection with the Session reference (emulator or manual check recorded in the PR).
- [x] Manual check on the deployed app: a conversation that shares details and an initiative produces a Lead with the expected score; recorded in the PR.

## Comments

- Delivered in [PR #14](https://github.com/gsbecerrag/cadre-ai-challenge/pull/14). Reviewer: one Important (filler text inflated the score) fixed in round 1 with three minors; scoped re-review: all addressed, no new breakage.
- Ruling: the five Qualification Signals are free-text strings the model reports; the code counts presence only, with a filler set ("unknown", "n/a", "not mentioned" …) that never scores and never overwrites a real value — a stated deviation from ADR-0009's typed signals.
- Ruling: one store seam — `ConversationStore` grows `upsert_lead` / `get_lead`; one Lead per Session in Firestore `leads/{session_id}`; later `capture_lead` calls merge (≥1 Contact Detail required only on the first call).
- Ruling: tools run as `async run(arguments, session_id)` so a tool can write through the async store; `escalate` and `show_walkthrough` adapted on the rebase; the registry never raises.
- Parked: Spanish filler spellings (pinned by the eval suite, ticket 13); `get_lead` returns the stored `qualified` rather than recomputing against a changed threshold (Console ticket); the Lead merge is read-modify-write.
- Deployed-app check (a conversation sharing fake details and an initiative produces a Lead with the expected score) is recorded by the controller after the merge.
