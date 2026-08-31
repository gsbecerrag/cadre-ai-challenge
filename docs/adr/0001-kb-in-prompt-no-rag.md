---
status: accepted
date: 2026-08-30
---

# Knowledge base compiled into a cached system prompt, no vector retrieval

The bot's entire knowledge base (KB) is a set of curated Markdown documents with stable KB section IDs, compiled at process start into one prompt-cached system-prompt block behind a `KnowledgeSource` seam. We chose this over retrieval because the corpus is ~25K tokens, the dominant risk is hallucinating facts that are absent from cadreai.com, and prompt caching makes reading the whole KB every turn cheaper than a retrieval pipeline is to build and evaluate before the deadline.

## Context

- cadreai.com is 111 URLs; the 33 non-article pages are fully server-rendered (the homepage carries ~22 KB of visible text). Curated into facts the bot may state, the KB is roughly 25K tokens, nowhere near a retrieval problem for a 1M-token-context model.
- The failure modes that matter are absence-of-fact hallucinations: the site has no booking calendar (every CTA goes to the /contact form), no portal URL or login, no AI Maturity Index page or quiz, no pricing except one $5,000 event, and no SOC 2 / ISO 27001 / DPA / data-residency statements. Retrieval cannot surface a fact that does not exist; the KB has to state the absence explicitly so the model escalates instead of inventing.
- Caching economics on the default model (Sonnet 5 via OpenRouter): $2.00/M uncached input, $0.20/M cache read, $4.00/M for a 1-hour cache write. A 25K-token KB costs ~$0.005 per turn from cache versus ~$0.05 uncached, and ~$0.10 to rewrite after an idle hour. Sonnet 5's 1,024-token cache minimum is far exceeded.
- Groundedness has to be measurable claim-by-claim (ADR-0008); that is only cheap when the judge can see the whole KB rather than a retrieved subset.
- Repo due 31 Aug. Every retrieval component (chunking, embeddings, index, retrieval evals) is a component that can be wrong in the live review.

## Decision

- The KB is a set of Markdown documents kept in git and reviewed like code. Every document has a stable ID and every heading a stable KB section ID; the compiled prompt keeps those IDs so answers cite the section they came from.
- At process start `KnowledgeSource` returns the documents; the prompt builder concatenates them into one system-prompt text block marked with an explicit cache breakpoint (1-hour TTL). The block is byte-stable across requests: no timestamps, session IDs or user names in the cached prefix; volatile content goes after it.
- Negative facts are first-class KB sections ("the site publishes no pricing", "there is no public portal login", "no security certifications are listed"), each paired with the redirect the bot must give (the /contact form, hello@gocadre.ai, (619) 324-3223).
- System-prompt rule: state only what a KB section states and cite it; otherwise escalate. This rule is what the hallucination-trap evals check.
- Phase 2, behind the same seam: a Firestore-backed `KnowledgeSource` so a Strategist can edit the KB from the console without a deploy (this is also where approved triage-report suggestions land, ADR-0005). Vector retrieval only when the trigger below fires.

## Considered Options

- Bedrock Knowledge Base — lost because it pins the runtime to AWS and Bedrock, which conflicts with the provider (ADR-0002) and platform (ADR-0003) choices, for a corpus that needs no retrieval.
- Firestore vector search — lost because it still needs an embedding pipeline, chunking decisions and retrieval-quality evals, and buys nothing under ~50 pages.
- Live ingestion of cadreai.com at runtime (Firecrawl or a crawler) — lost because the site is plain static HTML that a fetch already covers, and unreviewed marketing copy is exactly what should not reach the prompt; curation is the value.
- Anthropic document blocks with citations or the Files API — lost because they are first-party only (not via OpenRouter, Bedrock or Vertex) and citations are incompatible with structured outputs.

## Consequences

- Positive: no retrieval failure mode; every wrong answer is a prompt or KB defect, which is a one-file fix. Citations come for free. Cache read ~$0.005 per turn; ~1.2¢ per turn all-in; ~7¢ per six-turn session.
- Positive: the eval suite (ADR-0008) and the triage agent (ADR-0005) reason over the whole KB, so "KB gap" is a checkable triage category.
- Negative: every KB edit is a deploy until the Firestore-backed source exists; non-engineers cannot edit today.
- Negative: any byte change to the KB or the tool definitions invalidates the cache for every session; the cache is model-scoped, so a model switch (ADR-0002) starts cold; each idle hour costs one ~$0.10 rewrite.
- Negative: prompt cost grows linearly with KB size; at ~100K tokens the cached read alone is ~$0.02 per turn and latency to first token rises.
- Reopen when: the KB exceeds ~50 pages, non-engineers need to edit it routinely, or per-turn input cost dominates the cost model.

## Links

- Absent facts, page count, render mode: [cadreai-site-facts](../research/cadreai-site-facts.md)
- Cache pricing, TTLs, breakpoint limits: [openrouter-facts](../research/openrouter-facts.md), [claude-api-facts](../research/claude-api-facts.md)
- Related: [ADR-0002](0002-openrouter-sole-provider.md), [ADR-0005](0005-event-driven-triage-agent.md), [ADR-0008](0008-pytest-evals-over-ragas.md)
