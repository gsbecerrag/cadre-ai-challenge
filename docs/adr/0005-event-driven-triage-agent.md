---
status: accepted
date: 2026-08-30
---

# Feedback triage as an event-driven agent on Firestore triggers

A thumbs-down in the chat writes a feedback document; a Firebase Function fires on that document's write (create or update), makes one structured-output Sonnet 5 call, and writes a triage report keyed by the feedback ID that the console shows in a Triage tab. The chat API never knows the triage agent exists. We chose Firestore document triggers over in-process background tasks, Eventarc-to-Cloud-Run or Pub/Sub because they decouple triage from chat latency and failures, decode the event for us, and establish a pattern every later background agent reuses.

## Context

- The product vision is a self-improving loop: negative feedback → triage → a Strategist approves a KB patch and an eval case. The first step is the triage report; approval is Phase 2.
- Triage must not sit in the chat request path: a Sonnet 5 call over the KB plus the session takes seconds and costs roughly 5–8 cents uncached (~30K input tokens at $2/M plus output at $10/M); the user who clicked thumbs-down gains nothing by waiting for it.
- Cloud Run throttles CPU after the response is sent unless CPU-always-on is enabled, so a FastAPI background task can be starved or lost on scale-down. Firebase Functions Python gen2 receives Firestore document events already decoded; Eventarc-to-Cloud-Run delivers them as protobuf to decode by hand; Pub/Sub adds a topic, subscription and schema for a single consumer.
- Sonnet 5 on OpenRouter supports strict JSON-schema structured outputs (ADR-0002), so the report shape is enforced rather than parsed from prose.
- Firestore triggers are at-least-once; the handler must be idempotent.

## Decision

- Trigger: a write — create or update — of a feedback document (session ID, trace ID, rating, optional comment); see the amendment below for why not creation. Only a thumbs-down invokes the model; a thumbs-up is stored for scoring and skipped by the handler.
- Handler: loads the session's messages (already refuse-profile redacted, ADR-0006), the KB and the feedback; makes one Sonnet 5 call with a strict schema: category ∈ {kb_gap, wrong_escalation, hallucination, tone, pii, bug, other}, summary, evidence (quoted turns), optional suggested KB addition, optional suggested eval case, severity. Reusing the byte-identical KB prefix lets the call hit the chat cache when one is warm.
- Output: a triage report document keyed by the feedback ID (a redelivery overwrites the same document, so the handler is idempotent), plus a comment and a score on the Langfuse trace so the report sits next to the cost and the prompt.
- Console: a Triage tab lists reports through a realtime listener; a Strategist reads the suggestion. Approving it (writing to the Firestore-backed KB and appending the eval case) is Phase 2.
- Boundary: the chat API and the triage agent share the core package (prompt builder, KB loader, provider, redactor) but no runtime state; Firestore is the only channel between them. The same pattern is reserved for the lead-enrichment and handover-timeout agents.
- Fallback if Functions deployment is blocked on the day: the same handler as a FastAPI background task with CPU throttling disabled. Same code, different trigger.

## Amendment (ticket 14, implemented)

The trigger is `on_document_written("feedback/{feedback_id}")`, not the document's creation,
and the handler's first decision is `rating == "down"`. Ticket 12 made a Feedback document one
document per trace that a changed thumb *updates* — so a Visitor who presses 👍 and then 👎
produces a creation carrying `up` and an update carrying `down`, and a create-only trigger
would never see the thumbs-down at all. Watching writes moves that decision out of the
subscription and into the handler, where it is a tested line rather than a property of an
event filter; a thumbs-up (or an up-to-up update, which is the widget sending a comment after
the rating) still returns before the model is reached, so the cost argument above is unchanged.

Everything else in this decision stands as written: the report is keyed by the feedback ID, a
redelivery overwrites it, and the model runs again on that redelivery.

## Considered Options

- FastAPI background task in the API process — lost because CPU throttling and scale-down make completion unreliable, and it couples triage failures to the chat service.
- Eventarc → Cloud Run endpoint — lost because Firestore events arrive as protobuf that must be decoded by hand, for no benefit over Functions.
- Pub/Sub topic and subscriber — lost because it is a second piece of infrastructure for one producer and one consumer.
- Synchronous triage on the thumbs-down click — lost because the user waits seconds for a result they never see.
- Scheduled batch triage (OpenRouter exposes `:batch` model variants at a discount) — lost because it delays each report by up to a day for a volume that does not justify it.

## Consequences

- Positive: zero coupling; retries and scaling come from the platform; reports appear in the console as they land; every future background agent has the same shape.
- Positive: category and severity are schema-enforced, so the console can filter and the eval suite (ADR-0008) can consume suggested cases directly.
- Negative: two deployables; the core package is copied into the functions bundle at deploy time, which can drift (mitigated by one make target and CI exercising both).
- Negative: eventual consistency: a report appears seconds after the click, more on a cold start.
- Negative: idempotency is by document ID only; a changed model or prompt does not re-run old reports.
- Reopen when: feedback volume makes per-report cost matter (switch to Haiku or batching), or the approval flow needs ordering and human pauses (move to LangGraph, ADR-0004).

## Links

- Structured outputs, cost and batch variants via OpenRouter: [openrouter-facts](../research/openrouter-facts.md)
- Batch API availability by platform: [claude-api-facts](../research/claude-api-facts.md)
- Related: [ADR-0001](0001-kb-in-prompt-no-rag.md), [ADR-0003](0003-gcp-with-seams.md), [ADR-0004](0004-raw-tool-loop.md), [ADR-0006](0006-two-profile-pii.md), [ADR-0008](0008-pytest-evals-over-ragas.md)
