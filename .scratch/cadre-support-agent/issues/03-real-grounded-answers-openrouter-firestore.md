# 03: Real Grounded Answers on the public URL

**What to build:** A Visitor on the deployed URL asks "what does Cadre AI do?" and gets a real, streamed, cited answer from Claude Sonnet 5 through OpenRouter, and the conversation survives a page refresh and a new Cloud Run instance. This slice adds the production implementations behind the two seams from ticket 02: the OpenRouter `ModelProvider` (streaming over the OpenAI-compatible API, tool-call assembly across chunks, usage and cost read from the final usage chunk, the cache-control marker on the system block with the configured TTL, mid-stream errors that arrive on a successful HTTP status surfaced as a typed provider error, attribution headers) and the Firestore `ConversationStore` (Session document, message subcollection). Sessions become anonymous: an opaque server-issued id in an HTTP-only cookie; a configurable turn cap (default forty) ends the Session with a graceful message that includes the contact path. The deploy target binds the OpenRouter key from Secret Manager and the Cloud Run service account gets Firestore access. Phase P1.

**Blocked by:** 02 (First Turn end-to-end with the stub provider)

**Status:** ready-for-agent

- [ ] Parsing recorded OpenRouter stream fixtures yields the assembled text, assembled tool calls with arguments, and usage with cost; a fixture with a mid-stream error finish reason yields the typed provider error; covered at seam S2.
- [ ] The request body sent to the provider marks the system block cacheable with the configured TTL and includes the attribution headers; covered at S2 by inspecting the built request (no network).
- [ ] A first request without a cookie creates a Session and sets the cookie; a second request with the cookie continues the same Session; covered at seam S1 with the in-memory store.
- [ ] Reaching the turn cap returns the closing message with the contact path and stops accepting messages for that Session; covered at S1.
- [ ] The Firestore store round-trips a Session and its messages (verified against the Firestore emulator locally, or by a manual check recorded in the PR if the emulator is unavailable).
- [ ] On the deployed URL, a real question streams a cited answer; refreshing the page keeps the conversation; the PR records the URL and the observed cost from the usage chunk.
- [ ] The OpenRouter key is bound from Secret Manager in the deploy target; no secret appears in the image, the repository, or logs.
