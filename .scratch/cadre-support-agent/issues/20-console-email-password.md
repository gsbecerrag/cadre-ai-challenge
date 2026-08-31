# 20: Console sign-in with email and password

**What to build:** The Strategist Console signs in with Google only (ticket 10). A reviewer without a Google account needs a second path, so the sign-in page gains an email + password form alongside the Google button, calling Firebase Auth's `signInWithEmailAndPassword`. The demo account (`strategist@cadre-demo.example`) is already provisioned in Firebase Auth with `emailVerified: true`, and the password lives in Secret Manager as `console-demo-password` — so this is client UI and configuration only: the `TokenVerifier` and `firestore.rules` already accept any verified, allowlisted email regardless of which sign-in provider produced the ID token, and neither changes. Wrong credentials map to one honest, non-enumerating message. The demo address is added to `ADMIN_ALLOWED_EMAILS`'s deploy default and rendered into the committed `firestore.rules`. Phase P8 (scope addition).

**Blocked by:** 10 (Strategist Console with Google sign-in, Availability, and Leads)

**Status:** done

- [x] The sign-in page offers Google and email/password; wrong credentials show one clear message; the layout matches the Console tokens.
- [x] Signing in with the demo credentials issues a Firebase ID token that the existing verifier accepts (`emailVerified` true) — verified locally with a headless browser against the real Firebase project (fill the form, submit, assert the Console shell or the 403 page renders — either proves the token flow; with the LOCAL `.env` allowlist the demo address may 403, which is correct until the deploy: say which was observed).
- [x] `ADMIN_ALLOWED_EMAILS`'s deploy default and the committed `firestore.rules` include the demo address; no server code changed.
- [x] `make check` green; no new dependencies.
- [x] On the deployed app the demo credentials reach the Console (controller's check after merge + deploy + deploy-rules).

## Comments

- Delivered in [PR #25](https://github.com/gsbecerrag/cadre-ai-challenge/pull/25). Reviewer: Approved, no Critical/Important findings; two cosmetic minors parked (shared error slot; dead prop on the refusal branch).
- Ruling: zero server-side changes — the demo account is provisioned with a verified email, so the strict verifier and the rules stay exactly as reviewed in ticket 10; the credential is the secret and the allowlist stays the gate.
- The deployed check (the demo credentials reach the Console on the public URL) is recorded here after the merge + deploy + deploy-rules.
