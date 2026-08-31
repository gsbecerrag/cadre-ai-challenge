---
status: accepted
date: 2026-08-30
---

# Firebase Auth with an email allowlist for the console; prospects stay anonymous

the Strategist Console (leads, handover requests, triage reports, Strategist presence) requires Google sign-in through Firebase Auth, and the server accepts only ID tokens whose email is in `ADMIN_ALLOWED_EMAILS`; a shared `CONSOLE_TOKEN` header is the emergency fallback for the review. The chat is anonymous: a session is an opaque server-issued ID, no account, no login wall. The console is never open.

## Context

- Three user types: prospective clients and existing clients (both anonymous in chat) and Cadre Strategists (using the Console). The console displays raw lead contact details (ADR-0006), pending handover requests and triage reports; exposing it leaks every lead the bot ever captured.
- cadreai.com has no login anywhere and no public portal URL; the portal is described in marketing copy only and its CTA goes to /contact. There is no client directory to authenticate existing clients against, so the bot cannot verify "I am a client" and must answer portal-access questions generically and escalate.
- Firebase Auth is already part of the platform (ADR-0003), Google sign-in is what Cadre staff use, and an allowlist of a handful of strategist emails is the whole authorisation model. ID tokens are verifiable server-side with no session store.
- The console reads Firestore directly through realtime listeners for immediacy, so Firestore security rules and the API must enforce the same allowlist; that duplication is the price of realtime.
- The review happens on a public URL with evaluators who have no Cadre Google accounts; a fallback that does not depend on an OAuth consent screen working on the day is needed.

## Decision

- Console: Google sign-in via Firebase Auth. Every console, handover and triage endpoint verifies the ID token and checks the email against `ADMIN_ALLOWED_EMAILS`. Firestore rules restrict console reads and the presence write to signed-in users on the same allowlist (mirrored into the rules). The Strategist's UID becomes `strategist_id` on any handover request they accept.
- Fallback: if Google sign-in is unavailable in the demo environment, a shared `CONSOLE_TOKEN` sent as a header is accepted by the same endpoints. It is a secret in Secret Manager, never a default, and its use is logged. There is no third mode: the console is never open.
- Chat: no authentication. The server issues an opaque session ID stored in the browser; all session data is keyed by it. The chat client never talks to Firestore directly; chat endpoints accept only their own session ID and enforce a per-session turn cap. IP rate limiting is out of scope.
- Existing clients are treated as anonymous prospects. The bot explains that the portal exists for clients, that there is no public login on the site, and escalates to their Cadre contact or hello@gocadre.ai. Walkthrough cards over the demo portal are shown as illustration and labelled as mock data.

## Considered Options

- Google Cloud Identity Platform or a hand-rolled JWT — lost because it is more code for exactly the same allowlist.
- Cloud IAP in front of the console — lost because the SPA and API are one container on one origin (ADR-0003); IAP would need a load balancer and a split deployment.
- Anonymous Firebase Auth for prospects — lost because it adds a token round-trip and a user record with no per-user data to protect.
- Magic-link login for existing clients — lost because there is no client identity source to send links against; Phase 2 when Cadre exposes one.
- HTTP Basic auth on the console — lost because it carries no identity, so handover requests and triage approvals could not be attributed to a Strategist.

## Consequences

- Positive: minutes to implement; Strategist identity on every hand-over and every future approval; revoking access is removing an email.
- Positive: prospects never see a login wall, matching the site's own zero-login experience.
- Negative: Google accounts only; the allowlist lives in configuration, so adding a Strategist is a redeploy (Phase 2: the strategists collection becomes the allowlist that both the rules and the API read).
- Negative: two enforcement points (Firestore rules and API middleware) must stay in sync; a rules test covers this.
- Negative: no prospect identity means no cross-session continuity and nothing beyond a turn cap against a scripted client.
- Negative: the shared-token fallback is a single secret; it exists for the review and must be rotated or removed afterwards.
- Reopen when: existing clients need authenticated experiences (portal deep links, account-specific answers), a second tenant appears, or abuse makes IP or device-level rate limiting necessary.

## Links

- No login or portal URL on cadreai.com; contact channels: [cadreai-site-facts](../research/cadreai-site-facts.md)
- Related: [ADR-0003](0003-gcp-with-seams.md), [ADR-0006](0006-two-profile-pii.md), [ADR-0007](0007-daily-video-handover.md), [ADR-0009](0009-bant-lite-qualification.md)
