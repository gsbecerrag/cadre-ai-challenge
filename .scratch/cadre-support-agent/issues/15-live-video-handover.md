# 15: Live Hand-over on video inside the chat

**What to build:** A Qualified Lead accepts the offer while a Strategist is online, and within seconds a video call opens inside the chat; the Strategist sees the request on the Console, clicks Join, and the two are talking — the Visitor never leaves the page. This slice completes the `video` mode of the Handover Request: the server creates one Daily.co room per request with a short expiry and stores its URL on the request; the chat renders the prebuilt call iframe when the state reaches `pending_strategist`; the Console's Join moves the request to `strategist_joined` → `in_call` and renders the same room; End moves it to `ended`; if no Strategist joins within the configured window the request becomes `no_strategist_available` and degrades to a Callback with the Lead already captured. The `LIVE_HANDOVER_ENABLED` flag forces callback mode when off. The Daily key is bound from Secret Manager. Phase P5.

**Blocked by:** 11 (Callback Hand-over with a realtime Console notification)

**Status:** ready-for-agent

- [ ] Accepting in video mode calls the video adapter (faked in tests) to create a room and stores the room URL on the request; the adapter is never called in callback mode; covered at seam S1 with a fake video adapter.
- [ ] Join, End, and the timeout transition are validated against the state machine and rejected when out of order; the timeout path yields a Callback; covered at S1 and S2.
- [ ] The chat reducer shows the call frame at `pending_strategist`, the Strategist's name at `in_call`, and the "call ended" state; covered at seam S4.
- [ ] With the flag off, the whole path behaves exactly as ticket 11; covered at S1.
- [ ] On the deployed app with the Console on a second device: accept → room opens in chat → Join from Console → both sides see video → End. A short recording is attached to the PR.
