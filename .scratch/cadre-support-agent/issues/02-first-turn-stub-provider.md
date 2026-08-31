# 02: First Turn end-to-end with the stub provider

**What to build:** A Visitor types a message in the chat and watches the Assistant's answer stream in token by token, with a citation to a KB Section — running entirely locally with no external API. This slice creates the conversation pipeline: the `ModelProvider` seam with a scriptable stub implementation (canned text, tool calls, usage, or a provider error keyed by the last Visitor message), the `ConversationStore` seam with an in-memory implementation, the tool loop (assemble messages with the cached Knowledge Base block first, call the provider, execute tool calls, feed results back, at most four iterations, graceful stop), the Server-Sent Events contract (text delta, tool-call marker, card, hand-over offer, hand-over state, done with Trace id and usage, error with a user-safe message), the chat reducer in the web app that turns those events into chat state, and the Knowledge Base compiler that turns markdown topic files into KB Sections with stable ids and assembles the system prompt in the fixed order from the spec. Two or three Knowledge Base topics are enough here (services, industries, contact). Phase P1.

**Blocked by:** 01 (Hello-world Assistant live on Cloud Run)

**Status:** ready-for-agent

- [ ] Posting a message to the chat endpoint streams the event sequence text deltas → done, and the done event carries usage; covered at seam S1 with the stub provider and in-memory store.
- [ ] A stub script that returns a tool call causes the loop to execute the tool and continue, and the stream shows a tool-call marker before the final text; covered at S1.
- [ ] A stub script that returns a provider error produces exactly one error event with a user-safe message and no stack trace; covered at S1.
- [ ] The loop never exceeds four provider iterations per Turn; covered at S1.
- [ ] The compiler produces a KB Section for every heading in the topic files with ids of the form `topic#heading`, and the assembled system prompt lists the Knowledge Base block before any volatile content; covered at seam S2.
- [ ] The chat reducer turns a recorded event sequence into the expected chat state (streamed text accumulates, error renders as a friendly message); covered at seam S4 with one Vitest test.
- [ ] Running locally with the stub provider, the browser shows a streamed answer that cites a section id; a short screen recording or screenshot is attached to the PR.
