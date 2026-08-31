# 07: Demo Portal with mock data (parallel lane)

**What to build:** An existing client can open a demo of the Cadre Portal — a dashboard plus pages for AI tools, agents, and results/training — styled with Cadre's tokens, populated with plausible mock data for a "Demo client", and carrying a visible "Demo portal · mock data" badge on every page. It has no authentication and no state; it exists so Walkthrough Cards have a real destination and so the review can show what the Portal experience looks like. Routes live in the same web app under a portal path group and register through the app's route table without touching the chat or API code, so this ticket runs in parallel with tickets 02–06. Phase P1 (parallel).

**Blocked by:** 01 (Hello-world Assistant live on Cloud Run)

**Design reference:** [docs/design](../../../docs/design/README.md) — brief §2.1–2.2: the mock cadreai.com host page (sticky nav with "Talk to an AI Strategist", hero "From AI Confusion to AI Confidence.", partner strip, three-card grid, dark CTA "Track your AI results" → Portal, footer with the contact details) and the Portal (badge "Demo portal · mock data", tabs Dashboard / Tools / Agents / Results & Training, three stat cards, agents table with "● Live"). Ruling: the host page is in scope here — it is the page the chat widget floats over; it replaces ticket 01's placeholder shell and keeps the widget's mount point.

**Status:** in-progress

- [ ] Four portal pages render with mock data: dashboard (summary tiles), tools, agents (with per-agent results), results/training (progress); each shows the demo badge and shares a portal layout with navigation.
- [ ] The pages use the Cadre design tokens (colours, type, pill buttons) and are responsive.
- [ ] Each page has a stable route and, for the walkthrough destinations, stable element ids on the key panels (agents results, training progress, tools list).
- [ ] The site and portal code touch only their own route groups and the root/portal route registrations; `make check` stays green; no API changes.
- [ ] A screenshot of each page is attached to the PR.
- [ ] The root route renders the mock cadreai.com host page from the design (nav, hero, partner strip, cards, CTA, footer) with the chat widget's mount point preserved; the Portal pages match the design reference.
