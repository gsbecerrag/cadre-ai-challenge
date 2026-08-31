# 09: Lead capture with a Qualification Score computed in code

**What to build:** A Visitor shares their name, work email, company, phone, and role naturally during the conversation; the Assistant acknowledges without a lecture and a Lead is created for the Session with the five Qualification Signals it has learned (industry fit, company size or role, a concrete initiative or pain, a timeline or budget, explicit intent) and a Qualification Score computed in code as the count of signals present. Later details update the same Lead. The model never assigns the score; the threshold comes from configuration (default three). The system prompt gains qualification guidance: collect signals conversationally, never interrogate, call the tool as soon as any Contact Detail appears. Phase P2.

**Blocked by:** 03 (Real Grounded Answers on the public URL)

**Design reference:** [docs/design](../../../docs/design/README.md) — none directly: the design captures details through a "Your details" form card, which ticket 11 builds on top of this ticket's Lead upsert; this ticket implements the conversational `capture_lead` path from the spec. Ruling: the five Qualification Signals are the spec's (industry fit, company size or role, concrete initiative or pain, timeline or budget, explicit intent); the design's labels are superseded — see the rulings table.

**Status:** in-progress

- [ ] The score function returns the count of present signals (0–5) and the threshold comparison; covered at seam S2 with all boundary cases.
- [ ] A Turn in which the provider calls `capture_lead` creates a Lead bound to the Session with the raw Contact Details, the signals, and the computed score; a second call updates the same Lead rather than creating another; covered at seam S1 with the in-memory store.
- [ ] Contact Details on the Lead are stored raw (not tokenised) while the message history still passes through the `refuse` profile; covered at S1.
- [ ] The Firestore store persists Leads under their own collection with the Session reference (emulator or manual check recorded in the PR).
- [ ] Manual check on the deployed app: a conversation that shares details and an initiative produces a Lead with the expected score; recorded in the PR.
