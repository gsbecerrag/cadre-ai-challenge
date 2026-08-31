---
status: accepted
date: 2026-08-30
---

# A hand-written tool loop instead of an agent framework

The chat runtime is a single agent driven by an ~80-line loop: load the session's history, build the messages (cached KB prefix, history, new turn), call `ModelProvider` with the tool definitions, execute any tool calls in code, feed results back, repeat until the model stops, streaming text to the browser throughout. We chose this over PydanticAI, LangGraph, Google ADK or Bedrock AgentCore because the workload is one agent with five tools, the provider quirks must be handled where they are visible, and the review asks the author to defend every line of the prompt and API design.

## Context

- The MVP agent needs about five tools: `capture_lead` (writes a lead and its qualification score, ADR-0009), `escalate` (redirects to a human channel without a human joining), `show_walkthrough` (renders a walkthrough card over the demo portal), `offer_live_handover` (opens a handover request, ADR-0007) and, if time allows, `navigate_to` (in-app navigation). No multi-agent coordination and no workflow that outlives a request.
- OpenRouter's tool calling is the OpenAI shape and has rules a framework may not honour: the tool list must be sent on every request in the loop; streamed tool-call fragments must be accumulated; mid-stream failures arrive as HTTP 200 with finish_reason "error"; `temperature` is ignored on Sonnet 5; reasoning blocks must be passed back unchanged to preserve interleaved thinking.
- Prompt caching (ADR-0001) depends on byte-stable prefixes and deterministic tool serialisation. Frameworks that reorder or re-serialise messages and tools silently break the cache and the bill doubles.
- Evaluation weights: Claude Code proficiency 30%, architecture 25%. The reviewer will ask about system-prompt design and API structure; an abstraction between the author and those decisions is a liability in that conversation.
- State lives in Firestore (ADR-0003) and the API is stateless, so any in-process graph state a framework keeps would have to be externalised anyway.

## Decision

- One loop, one agent: history from `ConversationStore`, messages assembled with the cached KB block first and volatile content last, tools serialised in a fixed order, at most four model iterations per turn, then a graceful stop.
- Tools are plain functions over typed arguments; side effects go through seams (`ConversationStore`, `Notifier`), so the whole loop runs against the stub provider and the in-memory store in tests.
- Streaming: text deltas are forwarded to the browser over SSE as they arrive; tool calls execute once finish_reason signals the tool phase is complete; the final usage chunk is written to the trace.
- Failure handling is explicit and local: finish_reason "error" retries once; a malformed tool argument returns an error result to the model instead of crashing the turn; the iteration cap prevents loops.
- LangGraph is the named Phase-2 runtime. Trigger: a second agent that must coordinate with the first, or a durable multi-step workflow with human-in-the-loop pauses longer than a request.

## Considered Options

- PydanticAI (second choice) — lost because its provider abstraction sits exactly where the OpenRouter quirks and cache breakpoints must be controlled; its typing benefits are reproduced with plain schemas.
- LangGraph — lost because the MVP graph has one node and Firestore checkpointing needs a custom checkpointer before anything ships.
- Google ADK — lost because Claude runs behind a LiteLLM shim there, which drops the caching control we need.
- Bedrock AgentCore — lost because it is AWS-only (ADR-0003) and inherits Bedrock's feature gaps (ADR-0002).
- Anthropic SDK tool runner — lost because it is first-party only and does not work through OpenRouter.

## Consequences

- Positive: the author can explain every branch; every provider quirk is handled where it occurs; the loop runs fully offline against the stub provider, which is what the CI evals use (ADR-0008).
- Positive: adding a tool is adding a function and a schema; nothing else changes.
- Negative: retries, iteration caps, parallel tool-call handling and stream accumulation are our code and our bugs.
- Negative: no checkpointing or resumability; a crashed turn is lost and the user re-sends.
- Negative: when multi-agent arrives, the loop is rewritten, not extended.
- Reopen when: the Phase-2 trigger above fires, or a second `ModelProvider` implementation (Anthropic direct) needs a materially different message shape.

## Links

- Tool-calling and streaming rules: [openrouter-facts](../research/openrouter-facts.md)
- First-party tool-use surface and cache invalidation rules: [claude-api-facts](../research/claude-api-facts.md)
- Related: [ADR-0001](0001-kb-in-prompt-no-rag.md), [ADR-0002](0002-openrouter-sole-provider.md), [ADR-0003](0003-gcp-with-seams.md), [ADR-0007](0007-daily-video-handover.md), [ADR-0009](0009-bant-lite-qualification.md)
