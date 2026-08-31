# 08: Walkthrough Cards that open the Portal

**What to build:** A Visitor asks "how do I see my agents' results?" or "how do I get scored on the AI Maturity Index?" and the Assistant answers with a Walkthrough Card: a title, two to four steps, and one link to the destination — a demo Portal page for Portal tasks, or the contact form / a Hand-over for processes that start with a strategist. This slice adds the `show_walkthrough` tool (title, steps, destination id), a small catalogue of walkthrough destinations that maps ids to Portal routes and external links, the card event in the stream, the card component in the chat, and prompt guidance on when to use a card instead of prose. Phase P2.

**Blocked by:** 04 (Complete Knowledge Base and honest Escalation on Trap Questions), 07 (Demo Portal with mock data)

**Design reference:** [docs/design](../../../docs/design/README.md) — brief §2.5 kind 4 and §6: the Walkthrough Card (cream header band with title, numbered steps with circular badges, CTA "Open demo Portal", optional citations) and the reference flow: cited text ("Here's where that lives — the Portal tracks tools, agents, training, and results:") followed by the card "See your agents' results in the Portal" with its three steps.

**Status:** done

- [x] A Turn in which the provider calls `show_walkthrough` with a known destination streams a card event with the resolved link and the steps; an unknown destination id is rejected with a tool error the loop can recover from; covered at seam S1 with the stub.
- [x] The chat reducer places the card in the transcript at the right position relative to text; covered at seam S4 (extend the existing reducer test).
- [x] Clicking the card's link on the deployed app opens the matching Portal page in the same tab; recorded in the PR.
- [x] The Maturity Index walkthrough's destination is the contact form or a Hand-over, never an invented page; verified manually and recorded in the PR.
- [x] The Walkthrough Card matches the design reference (header band, numbered steps, CTA, citations).

## Comments

- Delivered in [PR #13](https://github.com/gsbecerrag/cadre-ai-challenge/pull/13). Reviewer: Approved, no Critical/Important findings; six minors fixed in a polish round; scoped re-review: all addressed, no breakage.
- Ruling: `show_walkthrough(title, steps[2..4], destination id)` with a Python catalogue; the model never supplies a URL; `card.destination` is `{id, label, href, external}` (first real definition of ticket 02's field).
- Ruling: the CTA dispatches `cadre:navigate`, handled by a listener inside the router with a same-origin guard, so the widget stays mounted; external destinations open in a new tab.
- Ruling: `maturity.get-scored` resolves to the published contact form (external) — never an invented page; the contact URL is the KB-published `https://www.cadreai.com/contact`.
- Carried forward: optional `language` on the escalation payload (from ticket 04); `OPEN_CHAT_EVENT` in the host page (from ticket 02). Parked: an English-only CTA label (`destination.label` is server-side); the internal CTA is a button, so cmd-click/open-in-new-tab is unavailable (matches the artboard).
- Deployed-app click-through (CTA opens the Portal page in the same tab with the widget open; the Maturity Index card goes to the contact form) is recorded by the controller after the merge.
