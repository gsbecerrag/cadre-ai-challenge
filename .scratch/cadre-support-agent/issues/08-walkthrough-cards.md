# 08: Walkthrough Cards that open the Portal

**What to build:** A Visitor asks "how do I see my agents' results?" or "how do I get scored on the AI Maturity Index?" and the Assistant answers with a Walkthrough Card: a title, two to four steps, and one link to the destination — a demo Portal page for Portal tasks, or the contact form / a Hand-over for processes that start with a strategist. This slice adds the `show_walkthrough` tool (title, steps, destination id), a small catalogue of walkthrough destinations that maps ids to Portal routes and external links, the card event in the stream, the card component in the chat, and prompt guidance on when to use a card instead of prose. Phase P2.

**Blocked by:** 04 (Complete Knowledge Base and honest Escalation on Trap Questions), 07 (Demo Portal with mock data)

**Status:** ready-for-agent

- [ ] A Turn in which the provider calls `show_walkthrough` with a known destination streams a card event with the resolved link and the steps; an unknown destination id is rejected with a tool error the loop can recover from; covered at seam S1 with the stub.
- [ ] The chat reducer places the card in the transcript at the right position relative to text; covered at seam S4 (extend the existing reducer test).
- [ ] Clicking the card's link on the deployed app opens the matching Portal page in the same tab; recorded in the PR.
- [ ] The Maturity Index walkthrough's destination is the contact form or a Hand-over, never an invented page; verified manually and recorded in the PR.
