# 23: "Research this Lead" on the Console

**What to build:** On every Qualified Lead card in the Console's Leads tab, a "Research this Lead" action runs the Research Agent through ticket 22's endpoint and shows it working: each `progress` line and each Research Finding as it lands, then the Lead Brief — company snapshot, person snapshot, talking points, the per-signal note beside each Qualification Signal row, the Findings as links that open in a new tab, and a footer naming the source ("Demo fixtures" for `fixture`), the model, the cost and when it was written; a brief with `complete: false` says it was cut short. The brief section is collapsible, open right after a run and collapsed when it was loaded from the feed. The button is disabled while a run is in flight and reads "Research again" once a brief exists; an unqualified card shows no button. Briefs are kept live by a `lead_briefs` Firestore listener with the same API polling fallback the other feeds use (`GET /api/console/briefs`), so a brief produced in another tab, or before a reload, appears on its card. The stream is read with the existing SSE reader (`web/src/chat/sse.ts`, generalised or copied — the reviewer accepts either, not a third parser) and a research reducer turns the events into card state. Docs in this ticket: README's Console section and `docs/demo-script.md` gain the research step. Phase P9.

**Blocked by:** None — builds against the event contract fixed in ticket 22; the deployed check waits for 22 to merge.

**Event contract:** verbatim from ticket 22 — `progress` {step, label}, `finding` {title, url, snippet, query}, `brief` {LeadBrief}, `done` {trace_id, usage}, `error` {message}; `LeadBrief` has `session_id`, `company_snapshot`, `person_snapshot`, `talking_points[]`, `signal_notes{five signal names}`, `findings[]`, `source`, `model`, `cost_usd`, `complete`, `created_at`. Every key always present. `GET /api/console/briefs` → `{"briefs": [LeadBrief, ...]}` newest first. A Firestore `lead_briefs/{session_id}` document has the same fields plus `updated_at`.

**Design reference:** [docs/design](../../../docs/design/README.md) §3.1 — keep the Lead card as it is; the brief is a section under the signals in the palette the Triage cards already use (cream `#f2efe4` boxes, `#999966` labels, the italic evidence block for Findings). The "Research this Lead" button is the card's one primary action: Cadre red, pill, full width under the score line.

**Status:** ready-for-agent

- [ ] S4: one Vitest test for the research reducer: progress → finding → brief → done produces the expected state (running with its lines and Findings, then the brief and idle); error produces a failed state with the message and no brief; a brief arriving from the feed replaces a stale one on the same Session.
- [ ] A Qualified Lead card shows "Research this Lead"; an unqualified card shows nothing.
- [ ] While running: the button is disabled; progress lines and Findings appear as they arrive, in order.
- [ ] After: the brief renders every field; each signal note sits beside its row; Findings link out in a new tab; the footer names the source, model, cost and time; a cut-short brief is labelled.
- [ ] Briefs from the listener or the polling fallback render on their cards on load, and the page's freshness line stays truthful (Live / Polling every 10s).
- [ ] `make check` green (eslint, tsc, vitest); README and the demo script updated; plan.md's P9 box for ticket 23 ticked in the PR.

## Comments
