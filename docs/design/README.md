# Design reference

The UI for the Assistant, the demo Portal, and the Strategist Console was designed in Claude Design before the tickets that build them ran. The artboards are the visual spec for every UI ticket; the tickets link here under **Design reference**.

- **Project:** <https://claude.ai/design/p/bfd373a0-ae2e-4190-81a5-ccc92864f13e> (the canonical, interactive version — open it to click through states)
- **Sources in this folder** (Claude Design `.dc.html` format: an HTML template with `{{ }}` bindings and a `DCLogic` script holding mock data and state; they render inside Claude Design, not standalone):
  - [`cadre-support-chat.dc.html`](cadre-support-chat.dc.html) — the Visitor side: a mock cadreai.com page, the chat widget and its states, and the demo Portal.
  - [`strategist-console.dc.html`](strategist-console.dc.html) — the Strategist side: Availability toggle, Handover queue and request detail, Callbacks, Triage reports.
- [`DESIGN-BRIEF.md`](DESIGN-BRIEF.md) — extracted facts: tokens, every view and state, component copy verbatim, the data shapes the mock data implies, a vocabulary check against [`CONTEXT.md`](../../CONTEXT.md), and the ticket mapping.
- [`claude-design-screen-map.md`](claude-design-screen-map.md) — the designer's own screen map and sync note.

## How tickets use this

A ticket's **Design reference** line names the artboard and the exact views/components it must match; its acceptance criteria include "matches the design reference" for those parts. Where the design and the spec disagree, **the spec wins** and the brief's vocabulary-check section lists the known mismatches (label text, state names) so implementers use the canonical terms from `CONTEXT.md` and the design's visual treatment.

## Later (Phase 2 idea, not planned)

Once the real React components exist, `/design-sync` can push them *up* to a Claude Design design-system project so future design iterations are built from the shipped components rather than mockups.

## Where the design and the spec disagree — rulings

The artboards were drawn from the spec but simplify it in places. These rulings (spec is the binding authority; recorded in the SDD ledger) tell implementers what to build; the design keeps its visual treatment.

| Design | Spec / CONTEXT.md | Ruling |
|---|---|---|
| Five signal labels: "Decision authority", "Budget conversation welcome", "Timeline < 6 months", "Fit industry", "Team size stated" | Five Qualification Signals: industry fit, company size or role, a concrete initiative or pain, a timeline or budget, explicit intent (ADR-0009) | Spec's five, displayed as "Industry fit", "Company size or role", "Initiative or pain", "Timeline or budget", "Explicit intent". "Decision authority" is dropped — it is not something the Assistant can establish from `capture_lead` arguments. |
| Request states `pending → in_call → ended` | `offered → accepted_by_user → pending_strategist → strategist_joined → in_call → ended`; exits `declined`, `no_strategist_available` (ADR-0007) | Spec's machine is the data model; the Console shows derived labels with the design's colours: **Pending** (offered / accepted_by_user / pending_strategist, `#db4545` pulsing), **In call** (strategist_joined / in_call, `#0a7d43` pulsing), **Ended** (`#999`), plus **Declined** (`#999`) and **Callback** (`#996`). "Claim & join call" performs `pending_strategist → strategist_joined → in_call` in one click. |
| Video requests in the Queue tab, callbacks as a separate table/entity | One Handover Request with `mode: video \| callback` | One type; the Callbacks tab is the `mode = callback` filter of the same collection. |
| Callbacks column "Scheduled for" + the chat's calendar picker card | No scheduling concept; a Callback means a Strategist reaches out | Out of scope for the MVP (plan.md cut log). Callbacks show "Requested"; the calendar card is not built. |
| "Your details" form card (Full name / Work email / Company) | Contact Details collected conversationally through `capture_lead` | Both: the tool path (ticket 09) and the form card (ticket 11), which posts to the same Lead upsert. Qualification Signals still come from the tool arguments. |
| No sign-in screen; Console always authenticated | Google sign-in + allowlist (ADR-0010) | Ticket 10 builds a minimal sign-in page in the Console's tokens. |
| Chat header presence line ("A strategist is online") driven by a demo prop | Availability from the Strategists' presence documents | Wired in ticket 11; until then the offline copy shows. |
| Quick-reply chips, EN/ES chrome toggle, docked/expanded panel | Not in the spec | Adopted in ticket 02 — cheap, and they make the demo legible. The Assistant's answer language still follows the Visitor's message. |
| Mock cadreai.com host page under the widget | Ticket 07 was Portal-only | Adopted into ticket 07 (parallel lane): the host page replaces ticket 01's placeholder and the widget floats over it, as on cadreai.com. |
| Triage categories shown: Knowledge gap, Wrong escalation | Seven categories | Ticket 14 adds chip styles for hallucination, tone, personal data, bug, other. |
| Data model calls the human party `user` | Visitor | Code and tests use Visitor; `role: "user"` stays only where the provider API requires it. |
