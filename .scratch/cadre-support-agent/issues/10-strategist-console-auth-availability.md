# 10: Strategist Console with Google sign-in, Availability, and Leads

**What to build:** A Strategist opens the Console, signs in with Google, and is admitted only if their email is on the configured allowlist; they toggle their Availability online or offline, and see Leads arrive in real time with Contact Details, signals, and score. This slice adds the Console route group in the web app (sign-in page, layout, Availability toggle, Leads list), Firebase Auth on the client, ID-token verification and the allowlist check on every Console endpoint in the API, a presence document per Strategist, Firestore security rules that mirror the allowlist for Console reads and the presence write, and a Firebase project configuration in the repository. Phase P2.

**Blocked by:** 09 (Lead capture with a Qualification Score computed in code)

**Design reference:** [docs/design](../../../docs/design/README.md) — artboard `strategist-console.dc.html`, brief §3 header and left nav: logo + "Strategist Console", the Availability control (label "Online" `#0a7d43` / "Offline" `#999` with the pill toggle), the identity block (avatar initial, name, email), the 200 px nav with tabs "Handover queue" / "Callbacks" / "Triage" and the red count badge (active tab weight 600, `#db4545` on `#f2efe4`). The design has no sign-in screen: build a minimal one in the same tokens (logo, "Sign in with Google", refusal message). The Leads list of this ticket uses the queue card style from §3.1.

**Status:** done

- [x] Console endpoints reject a missing or invalid token and an email outside the allowlist, and accept an allowlisted one; covered at seam S1 with the auth dependency overridden by a fake verifier.
- [x] Setting Availability writes the Strategist's presence document with `online` and a timestamp; reading Availability reports whether any Strategist is online; covered at S1 with the in-memory store.
- [x] Firestore rules allow allowlisted signed-in users to read Leads, Handover Requests, and Triage Reports and to write only their own presence document; rules are deployed with the app (rules unit tests are out of scope; a manual denial check is recorded in the PR).
- [x] On the deployed app, signing in with the allowlisted account shows the Console; a non-allowlisted account is refused with a clear message; toggling online updates the presence document; a new Lead appears without a refresh. Screenshots attached to the PR.
- [x] The Console shell (header, Availability control, identity, left nav with badge) matches the design reference; the sign-in page uses the same tokens.

## Comments

- Delivered in [PR #17](https://github.com/gsbecerrag/cadre-ai-challenge/pull/17). Reviewer: Approved — audience-checked token verification and `email_verified` at both enforcement points confirmed against the `google-auth` source; one Important (the Firebase SDK in the Visitor bundle) and minors fixed in round 1; scoped re-review: all addressed, no new breakage.
- Ruling: `TokenVerifier` seam with one production adapter and a fake for S1; `current_strategist` is a router-level dependency (401 missing/invalid, 403 not allowlisted); an empty allowlist admits nobody; `CONSOLE_AUTH=fake` is startup-fatal outside development.
- Ruling: presence lives in `strategists/{uid}` through the one store seam (`set_availability`, `get_availability`, `any_strategist_online`); Leads via `GET /api/console/leads` plus the browser's `onSnapshot` with a polling fallback.
- Ruling: the Console is lazy-loaded so the Firebase SDK never ships to Visitors; the chat widget does not render on `/console`; nav tabs Leads / Handover queue / Callbacks / Triage (11 / 11 / 14 fill the last three).
- Ruling: Firestore rules mirror the allowlist (rendered by `scripts/render-firestore-rules.py`), deny Sessions and messages by default, and allow a Strategist to write only their own presence document with a fixed field set; `make deploy-rules` is run by the controller after the merge; the deploy target sets `ADMIN_ALLOWED_EMAILS`.
- Parked: the store's `StrategistIdentity` parameter couples the store seam to the auth type; cross-surface links are full page loads; no `CONSOLE_TOKEN` fallback (ADR-0010) built.
- Deployed checks: the controller records the API 401/403 and the rules denial check after the deploy; the signed-in walkthrough (sign in with the allowlisted account, toggle Availability, watch a Lead arrive) needs Galo's Google session — recorded here when done.
- Deployed-app check recorded: [docs/transcripts/2026-08-31-deployed-checks-06-10.md](../../../docs/transcripts/2026-08-31-deployed-checks-06-10.md) — revision `56aa909` on the public URL.
