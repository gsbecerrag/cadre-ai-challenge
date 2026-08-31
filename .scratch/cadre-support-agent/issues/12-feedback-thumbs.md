# 12: Thumbs up/down becomes Feedback and a Langfuse score

**What to build:** A Visitor gives a thumbs-up or thumbs-down at the end of an exchange, optionally adding a sentence, and the Feedback is stored with the Session id and the Trace id of the Turn it judges, and mirrored to Langfuse as a score on that Trace. The buttons appear after each Assistant answer; a choice can be changed once. Phase P4.

**Blocked by:** 06 (Every Turn is a Trace with cost in Langfuse)

**Design reference:** [docs/design](../../../docs/design/README.md) — brief §2.5 kind 9: the feedback card ("How was your conversation with {Strategist}?" with 👍/👎, thumbs-up hover border `#0a7d43`) and its done state with the thanks/apology copy. Ruling: the same component also appears after each Assistant answer, inline, as the spec requires.

**Status:** ready-for-agent

- [ ] Posting Feedback with a rating, an optional comment, the Session id and the Trace id writes a Feedback document and calls the tracing sink with a score of 1 or 0 on that Trace; a comment passes through the `full` Redaction Profile; covered at seam S1 with the in-memory store and the fake tracer.
- [ ] Feedback for an unknown Session or a Trace id that does not belong to it is rejected; covered at S1.
- [ ] The chat shows the buttons after each answer and reflects the chosen state; covered at seam S4 (extend the reducer test).
- [ ] On the deployed app, a thumbs-down appears as a score on the Trace in Langfuse and as a document in Firestore; screenshot attached to the PR.
- [ ] The feedback buttons and their done states match the design reference.
