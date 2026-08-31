# 02: First Turn end-to-end with the stub provider

**What to build:** A Visitor types a message in the chat and watches the Assistant's answer stream in token by token, with a citation to a KB Section — running entirely locally with no external API. This slice creates the conversation pipeline: the `ModelProvider` seam with a scriptable stub implementation (canned text, tool calls, usage, or a provider error keyed by the last Visitor message), the `ConversationStore` seam with an in-memory implementation, the tool loop (assemble messages with the cached Knowledge Base block first, call the provider, execute tool calls, feed results back, at most four iterations, graceful stop), the Server-Sent Events contract (text delta, tool-call marker, card, hand-over offer, hand-over state, done with Trace id and usage, error with a user-safe message), the chat reducer in the web app that turns those events into chat state, and the Knowledge Base compiler that turns markdown topic files into KB Sections with stable ids and assembles the system prompt in the fixed order from the spec. Two or three Knowledge Base topics are enough here (services, industries, contact). Phase P1.

**Blocked by:** 01 (Hello-world Assistant live on Cloud Run)

**Design reference:** [docs/design](../../../docs/design/README.md) — artboard `cadre-support-chat.dc.html`, brief §2.3–2.5 and §2.7: the launcher (fixed bottom-right, 58 px circle, ink `#0c0407`), the panel shell (docked 392 px / expanded, radius 24 px, header gradient with the avatar "C", title "Cadre AI Assistant", presence line, EN/ES toggle for chrome strings, expand and close), the `text` and `typing` message kinds, citation chips (monospace pill on `#f2efe4`), the input bar (placeholder "Ask about services, industries, pricing…", send `↑`), quick-reply chips, and the `msgin` entrance. The presence line shows the offline copy until ticket 11 wires Availability; the host page under the widget is ticket 07 (keep a stable mount point).

**Status:** done

- [x] Posting a message to the chat endpoint streams the event sequence text deltas → done, and the done event carries usage; covered at seam S1 with the stub provider and in-memory store.
- [x] A stub script that returns a tool call causes the loop to execute the tool and continue, and the stream shows a tool-call marker before the final text; covered at S1.
- [x] A stub script that returns a provider error produces exactly one error event with a user-safe message and no stack trace; covered at S1.
- [x] The loop never exceeds four provider iterations per Turn; covered at S1.
- [x] The compiler produces a KB Section for every heading in the topic files with ids of the form `topic#heading`, and the assembled system prompt lists the Knowledge Base block before any volatile content; covered at seam S2.
- [x] The chat reducer turns a recorded event sequence into the expected chat state (streamed text accumulates, error renders as a friendly message); covered at seam S4 with one Vitest test.
- [x] Running locally with the stub provider, the browser shows a streamed answer that cites a section id; a short screen recording or screenshot is attached to the PR.
- [x] The chat widget matches the design reference for the launcher, panel shell, text/typing bubbles, citation chips, input bar and quick replies (tokens, radii, copy); any deviation is listed in the PR.

## Comments

- Delivered in [PR #9](https://github.com/gsbecerrag/cadre-ai-challenge/pull/9). Reviewer: three Important findings (KB missing from the image + silent empty KB; no `cadre:open-chat` listener; orphaned Visitor message on a failed Turn) fixed in round 1; scoped re-review: all addressed, no new breakage.
- Ruling: **a Turn is stored only when it completes** — nothing is persisted on a provider error or a dropped connection, so a Session never holds a Visitor message without its reply (ticket 03's `visitor → user` mapping would reject consecutive user messages).
- Ruling: the app fails fast on an empty Knowledge Base; `knowledge/` ships in the image (`!knowledge/*.md` un-ignored in both `.dockerignore` and `.gcloudignore`).
- Ruling: the session cookie stays opaque and unsigned here; signing lands with ticket 03's Session work (the spec budgets the session secret there).
- Ruling: S4 "one web reducer test" = one test file with several cases.
- Ruling: quick replies, the EN/ES chrome toggle, and the docked/expanded panel are in (design ruling); the "agents' results" quick reply escalates until ticket 08's Walkthrough Card exists.
- Carried forward: the 4th-pass tools still run at the iteration cap (revisit in ticket 04 with the Escalation rules); `sse.ts` is coupled to `core/sse.py`'s framing (comment in place; ticket 03 must not change framing alone); `HostPage.tsx` uses the literal event name rather than `OPEN_CHAT_EVENT` (ticket 08 touches both sides).
