---
status: accepted
date: 2026-08-30
---

# OpenRouter as the sole runtime LLM provider

All runtime model calls (chat, judge, triage) go through OpenRouter's OpenAI-compatible API behind a `ModelProvider` seam with one production implementation and one stub provider. Cadre supplied the OpenRouter key, cadreai.com itself lists OpenRouter among the LLM platforms Cadre works with, and OpenRouter passes Anthropic prompt caching through, which is what makes the KB-in-prompt design (ADR-0001) affordable.

## Context

- Cadre supplied an OpenRouter key for the take-home. The homepage and /ai-engineering logo rows name OpenRouter alongside Claude, OpenAI and Gemini, and the homepage badge reads "Anthropic & OpenAI Partner". A vendor-neutral gateway is on-brand.
- Cadre's own model-selection article (29 May 2026) prescribes tiering tasks across Haiku, Sonnet and Opus with a cost gap that "can exceed 90 percent per task". Showing model choice per task (chat, judge, triage) is part of the pitch.
- OpenRouter facts that drove the choice: 396 models behind one API; no inference markup (5.5% fee on credit purchase only); `usage.cost` returned on every response (the opt-in flag is deprecated); tool calling and structured outputs in OpenAI shape; Anthropic `cache_control` breakpoints pass through, including the 1-hour TTL and the four-breakpoint limit; sticky provider routing keyed by a session ID (10-minute idle expiry); Langfuse's OpenAI drop-in works and records the returned cost directly.
- Prices per 1M tokens (input / output / cache read): Sonnet 5 $2 / $10 / $0.20; Haiku 4.5 $1 / $5 / $0.10; GPT-5.6-sol $2 / $10 / $0.20; Gemini 3.7 Flash $0.75 / $3.75 / $0.075.
- Gotchas we must code around: Sonnet 5 and GPT-5.x silently ignore `temperature`; mid-stream errors arrive as HTTP 200 with finish_reason "error"; the Sonnet 5 cache minimum is not stated in OpenRouter's docs (1,024 tokens per Anthropic's); Sonnet 5's Vertex-hosted endpoints do not list structured outputs, so `require_parameters` must be set when a JSON schema is requested; no numeric rate limit for paid keys is documented.
- Bedrock feature gaps (no web search or fetch, Files API, Agent Skills, MCP connector, Batches, mid-conversation system messages, server-side fallbacks) make it a poor default, and its `us-east-1` Sonnet 5 endpoint is priced at $2.20 / $11.

## Decision

- `ModelProvider` has exactly one production implementation (OpenRouter chat completions, streaming) and a stub provider that replays canned text and tool calls for unit tests, CI evals and load tests.
- Model IDs are configuration, not code: chat = anthropic/claude-sonnet-5, judge = anthropic/claude-haiku-4.5, triage = anthropic/claude-sonnet-5. The benchmark set is Sonnet 5, Haiku 4.5, GPT-5.6-sol and Gemini 3.7 Flash, run through the eval suite (ADR-0008).
- The KB system block carries an explicit cache breakpoint with 1-hour TTL, and every request sends the session ID for sticky routing so consecutive turns of a session reach the same upstream and its cache.
- finish_reason "error" is a failed turn: retry once, then a graceful message. `temperature` is never relied upon. `require_parameters` is set whenever structured output is requested. Attribution headers are sent so usage shows under the app name.
- Per-request `usage.cost` and cached-token counts are recorded on the Langfuse trace; that, not a price table, is the cost source of truth.
- Not done now: OpenRouter's model-fallback list. Cross-provider fallback would silently mask an upstream outage during evaluation; Phase 2 once error rates have been measured.

## Considered Options

- Anthropic API direct — lost because no key was supplied and it forecloses the cross-vendor benchmark; it is the named Phase-2 second `ModelProvider` implementation (unlocks Files API, citation blocks, mid-conversation system messages).
- Amazon Bedrock — lost on the feature gaps above plus AWS lock-in that conflicts with ADR-0003.
- Google Vertex AI direct — lost because it needs its own SDK and auth plumbing for one vendor, offers no server-side fallbacks or Files API, and carries partner pricing.
- One adapter per vendor SDK — lost because four SDKs and four caching dialects would be maintained to get a benchmark OpenRouter provides for free.

## Consequences

- Positive: a model switch is an environment variable; one client library; cost per turn from the response; a cross-vendor benchmark for the review with no extra code.
- Positive: the stub provider makes the API and the evals runnable with no key, which is what CI uses.
- Negative: one extra network hop and a third party in the data path. `data_collection: deny` and zero-data-retention routing exist but not every upstream supports them; enterprise data-residency questions are Phase 2.
- Negative: Anthropic-only features are unavailable; none are needed by the MVP.
- Negative: paid-key rate limits are undocumented, so the capacity model uses a measured tokens-per-minute figure rather than a published one.
- Reopen when: Cadre wants first-party contracts or ZDR, measured OpenRouter latency or error rate exceeds budget, or a first-party-only feature becomes necessary.

## Links

- Pricing, caching pass-through, tool calling, gotchas, routing flags: [openrouter-facts](../research/openrouter-facts.md)
- First-party surface and Bedrock / Vertex gaps: [claude-api-facts](../research/claude-api-facts.md)
- Partner statements and OpenRouter logo placement: [cadreai-site-facts](../research/cadreai-site-facts.md)
- Related: [ADR-0001](0001-kb-in-prompt-no-rag.md), [ADR-0003](0003-gcp-with-seams.md), [ADR-0008](0008-pytest-evals-over-ragas.md)
