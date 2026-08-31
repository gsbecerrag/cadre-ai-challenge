# 03: Real Grounded Answers on the public URL

**What to build:** A Visitor on the deployed URL asks "what does Cadre AI do?" and gets a real, streamed, cited answer from Claude Sonnet 5 through OpenRouter, and the conversation survives a page refresh and a new Cloud Run instance. This slice adds the production implementations behind the two seams from ticket 02: the OpenRouter `ModelProvider` (streaming over the OpenAI-compatible API, tool-call assembly across chunks, usage and cost read from the final usage chunk, the cache-control marker on the system block with the configured TTL, mid-stream errors that arrive on a successful HTTP status surfaced as a typed provider error, attribution headers) and the Firestore `ConversationStore` (Session document, message subcollection). Sessions become anonymous: an opaque server-issued id in an HTTP-only cookie; a configurable turn cap (default forty) ends the Session with a graceful message that includes the contact path. The deploy target binds the OpenRouter key from Secret Manager and the Cloud Run service account gets Firestore access. Phase P1.

**Blocked by:** 02 (First Turn end-to-end with the stub provider)

**Status:** done

- [x] Parsing recorded OpenRouter stream fixtures yields the assembled text, assembled tool calls with arguments, and usage with cost; a fixture with a mid-stream error finish reason yields the typed provider error; covered at seam S2.
- [x] The request body sent to the provider marks the system block cacheable with the configured TTL and includes the attribution headers; covered at S2 by inspecting the built request (no network).
- [x] A first request without a cookie creates a Session and sets the cookie; a second request with the cookie continues the same Session; covered at seam S1 with the in-memory store.
- [x] Reaching the turn cap returns the closing message with the contact path and stops accepting messages for that Session; covered at S1.
- [x] The Firestore store round-trips a Session and its messages (verified against the Firestore emulator locally, or by a manual check recorded in the PR if the emulator is unavailable).
- [x] On the deployed URL, a real question streams a cited answer; refreshing the page keeps the conversation; the PR records the URL and the observed cost from the usage chunk.
- [x] The OpenRouter key is bound from Secret Manager in the deploy target; no secret appears in the image, the repository, or logs.

## Comments

- Delivered in [PR #11](https://github.com/gsbecerrag/cadre-ai-challenge/pull/11). Reviewer: Approved; three Should-Fix hardening items (raw-byte cookie 500, lost-update race on concurrent appends, IAM grant skipped for existing secrets) fixed in round 1; scoped re-review: all addressed, no new breakage.
- Ruling: the session cookie is signed here (`<id>.<hmac-sha256>` with `SESSION_COOKIE_SECRET`, required in production); any cookie this service did not issue earns a fresh Session, never an error.
- Ruling: the cache marker is an explicit `cache_control` breakpoint on the system content block (ADR-0002's wording), proven by 2,817 cached tokens on the second Turn; `ProviderRequest.session_id` feeds OpenRouter's sticky routing.
- Ruling: the Turn cap reuses `MAX_TURNS_PER_SESSION`; at the cap nothing is stored and the provider is not called.
- Ruling: the implementer verified locally against the real provider (total spend $0.032) and the controller verified the Firestore round-trip against the real project; the deployed-URL check and observed cost are recorded below after the merge.
- Follow-ups parked: Session expiry (a Firestore TTL policy on `updated_at`); closing the provider's HTTP client via a lifespan hook when a ticket adds one; the first-deploy referer fallback; a typed check on the stored `role`.
- Deployed-app check recorded: [docs/transcripts/2026-08-31-deployed-checks.md](../../../docs/transcripts/2026-08-31-deployed-checks.md) — revision `0b118a7` on the public URL with Claude Sonnet 5 through OpenRouter and Firestore Sessions; six scenarios, three Trap Questions, Spanish, and a refresh pair; ~0.6–1.3¢ per cached Turn.
