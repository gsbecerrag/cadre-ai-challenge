# 18: In-app navigation from a Walkthrough Card (optional)

**What to build:** When a Walkthrough Card's destination is inside the demo Portal, clicking it navigates the single-page app to that page and briefly highlights the target panel — the Assistant literally shows the Visitor where things are. This slice adds a `navigate_to` tool (route id, element id) resolved through the walkthrough catalogue, a navigation event in the stream, and a highlight behaviour on the target element; the chat stays open alongside the Portal page. Optional; Phase P6.

**Blocked by:** 08 (Walkthrough Cards that open the Portal)

**Status:** wontfix

- [ ] A Turn in which the provider calls `navigate_to` with a known route and element streams a navigation event; unknown ids are rejected; covered at seam S1 with the stub.
- [ ] The reducer records the pending navigation and the app performs it, pulsing the target; covered at seam S4 for the reducer part.
- [ ] On the deployed app, "show me where my agents' results are" navigates to the agents page and highlights the results panel while the chat remains visible; recording attached to the PR.

## Comments

- 2026-08-31 — wontfix (ticket 19, [PR #28](https://github.com/gsbecerrag/cadre-ai-challenge/pull/28)): Deadline, and the least load-bearing of the three optional tickets: a Walkthrough Card already opens the Portal page with the chat still open. Recorded in plan.md §7.
