# 07: Demo Portal with mock data (parallel lane)

**What to build:** An existing client can open a demo of the Cadre Portal — a dashboard plus pages for AI tools, agents, and results/training — styled with Cadre's tokens, populated with plausible mock data for a "Demo client", and carrying a visible "Demo portal · mock data" badge on every page. It has no authentication and no state; it exists so Walkthrough Cards have a real destination and so the review can show what the Portal experience looks like. Routes live in the same web app under a portal path group and register through the app's route table without touching the chat or API code, so this ticket runs in parallel with tickets 02–06. Phase P1 (parallel).

**Blocked by:** 01 (Hello-world Assistant live on Cloud Run)

**Status:** ready-for-agent

- [ ] Four portal pages render with mock data: dashboard (summary tiles), tools, agents (with per-agent results), results/training (progress); each shows the demo badge and shares a portal layout with navigation.
- [ ] The pages use the Cadre design tokens (colours, type, pill buttons) and are responsive.
- [ ] Each page has a stable route and, for the walkthrough destinations, stable element ids on the key panels (agents results, training progress, tools list).
- [ ] The portal code touches only its own route group and one route registration; `make check` stays green; no API changes.
- [ ] A screenshot of each page is attached to the PR.
