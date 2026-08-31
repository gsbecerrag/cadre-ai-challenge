# 11: Callback Hand-over with a realtime Console notification

**What to build:** A Qualified Lead is asked once — "would you like to talk to a strategist right now?" — and on accepting, a Handover Request appears on the Strategist's Console the same instant, with a browser notification and a sound; when no Strategist is online (or the live flag is off) the request is a Callback: the Visitor is told a strategist will reach out and sees their details confirmed. This slice adds the `offer_live_handover` tool, exposed to the model only when the Session's Lead meets the threshold and no offer has been made; the Handover Request document and its state machine (`offered → accepted_by_user → pending_strategist → …`, exits `declined`, `no_strategist_available`, mode `callback` when nobody is online or the flag is off; every transition validated server-side); the hand-over offer card and accept/decline actions in the chat; the Console queue (pending, callbacks) via realtime listener with notification and sound; and the `Notifier` seam whose production implementation is the Firestore write itself. Video mode is ticket 15. Phase P2.

**Blocked by:** 10 (Strategist Console with Google sign-in, Availability, and Leads)

**Design reference:** [docs/design](../../../docs/design/README.md) — brief §2.5 kinds 5–7 and §3.1–3.2. Chat side: the "Your details" card (Full name / Work email / Company, "Share details", done state "✓ Details shared with the strategist") posting to this ticket's Lead endpoint (reusing ticket 09's upsert), the hand-over offer card ("Do you want to jump into a call with our experts?", Yes / "Keep chatting"), the decline line, and the Callback confirmation card ("A strategist will call you back"). Console side: the "Handover requests" list cards (name, pulsing state badge, company · industry, time, "score n/5"), the request detail (name header with the contact line, Qualification panel with ✓/— rows, Request panel with Mode / State / Session / Trace, "Conversation so far" bubbles) and the Callbacks table (Lead / Contact / Requested / Score). Rulings (see the rulings table): the spec's state machine with derived display labels; one Handover Request type with a mode field (Callbacks tab = `callback` filter); the calendar picker and "Scheduled for" slot are out of scope; the chat header's presence line is wired to Availability here.

**Status:** done

- [x] The offer tool is absent from the tool list below the threshold, present at or above it, and absent again after one offer in the Session; covered at seam S1 by inspecting the tools the stub provider receives.
- [x] Accepting creates a Handover Request in `callback` mode when no Strategist is online or `LIVE_HANDOVER_ENABLED` is off, and in `video` mode otherwise (mode only; the video path is ticket 15); declining sets `declined`; invalid transitions are rejected; covered at S1 with the in-memory store and notifier.
- [x] The state machine's allowed transitions are covered exhaustively at seam S2.
- [x] The chat reducer handles the offer card and the hand-over state events (offered, accepted, callback confirmed, declined); covered at seam S4.
- [x] On the deployed app with the Console open on a second screen: accepting the offer makes the request appear within a second with a notification and sound; the Visitor sees the Callback confirmation. A short recording is attached to the PR.
- [x] The chat cards (details, offer, callback) and the Console queue, request detail and Callbacks table match the design reference, using the spec's state names and signal labels.

## Comments

- Delivered in [PR #22](https://github.com/gsbecerrag/cadre-ai-challenge/pull/22). Reviewer: one Important (the details card recomputed `qualified` at the hard-coded threshold) and minors fixed in round 1 (the round was interrupted by a laptop failure and completed by a fresh implementer, replayed test-first); scoped re-review: all addressed, no new breakage.
- Ruling: the offer is gated by a per-Turn availability predicate on the tool registry (Lead qualified, no request yet), once per Session; the request is created at the offer and its mode is decided at acceptance — ADR-0007 carries an amendment paragraph to that effect.
- Ruling: accept is one store write after validating both hops; foreign Session → 404, invalid transition → 409; the production `Notifier` is the Firestore write itself.
- Ruling: the Console rings when the Visitor accepts (a request newly in `pending_strategist`), not when the offer appears; the initial snapshot is silent.
- Carried eval findings landed here: a job title counts as `company_size_or_role`; "send everything learned so far" prompt rule; the pricing copy's "event ticket" qualifier.
- Parked: memoising the exposure predicate per Turn; the detail re-fetch on every poll; the silent default notifier; spec §Hand-over wording on `no_strategist_available` vs `pending_strategist` + callback.
- Deployed two-screen check and recording (accept → ring on the Console within a second; the Visitor sees the Callback confirmation) needs Galo's Google session — recorded here when done.
