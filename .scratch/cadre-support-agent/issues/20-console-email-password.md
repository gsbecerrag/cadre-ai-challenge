# 20: Console sign-in with email and password

**What to build:** The Strategist Console signs in with Google only (ticket 10). A reviewer without a Google account needs a second path, so the sign-in page gains an email + password form alongside the Google button, calling Firebase Auth's `signInWithEmailAndPassword`. The demo account (`strategist@cadre-demo.example`) is already provisioned in Firebase Auth with `emailVerified: true`, and the password lives in Secret Manager as `console-demo-password` — so this is client UI and configuration only: the `TokenVerifier` and `firestore.rules` already accept any verified, allowlisted email regardless of which sign-in provider produced the ID token, and neither changes. Wrong credentials map to one honest, non-enumerating message. The demo address is added to `ADMIN_ALLOWED_EMAILS`'s deploy default and rendered into the committed `firestore.rules`. Phase P8 (scope addition).

**Blocked by:** 10 (Strategist Console with Google sign-in, Availability, and Leads)

**Status:** in-progress

- [ ] The sign-in page offers Google and email/password; wrong credentials show one clear message; the layout matches the Console tokens.
- [ ] Signing in with the demo credentials issues a Firebase ID token that the existing verifier accepts (`emailVerified` true) — verified locally with a headless browser against the real Firebase project (fill the form, submit, assert the Console shell or the 403 page renders — either proves the token flow; with the LOCAL `.env` allowlist the demo address may 403, which is correct until the deploy: say which was observed).
- [ ] `ADMIN_ALLOWED_EMAILS`'s deploy default and the committed `firestore.rules` include the demo address; no server code changed.
- [ ] `make check` green; no new dependencies.
- [ ] On the deployed app the demo credentials reach the Console (controller's check after merge + deploy + deploy-rules).
