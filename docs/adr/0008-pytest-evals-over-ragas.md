---
status: accepted
date: 2026-08-30
---

# Evals as a pytest suite with JSONL cases and an LLM judge, not RAGAS

The eval suite is pytest over JSONL case files: 20 in-KB correctness cases, 20 hallucination traps and 10 qualification/tool cases, scored on correctness (LLM judge), escalation correctness (binary), tool correctness (binary) and groundedness (claim-by-claim against KB sections). Results go to Langfuse datasets, the same suite drives the cross-model benchmark, and a stub-provider subset runs in CI. RAGAS lost because there is no retrieval to measure.

## Context

- The KB is in the prompt (ADR-0001); RAGAS's headline metrics (context precision, recall, relevancy) measure a retriever that does not exist. What remains of RAGAS is an answer-faithfulness judge, which is a few lines of pytest.
- The risk profile is specific: the site publishes no pricing (except one $5,000 event), no portal URL, no booking link, no Maturity Index page, no SOC 2 / ISO / DPA statements, no headcount or founding year, and no partnership details for Google, AWS, Snowflake or Salesforce beyond logos. Each is a hallucination trap the bot must escalate on, plus competitor comparisons and prompt injection. These are binary judgements, not similarity scores.
- The brief demands verified generated code, and the review weights architecture and Claude Code proficiency. A suite the author wrote and hand-validated is more defensible than a framework's opaque scores.
- Judge economics: Haiku 4.5 costs $1 / $5 per 1M tokens, so a judge call is ~$0.002; a full 50-case run against Sonnet 5 with the cached KB is well under $1 (~25K cached tokens at $0.20/M per case). Haiku's 4,096-token cache minimum means judge prompts do not cache, which is fine at that size.
- The benchmark (ADR-0002) needs one harness that runs unchanged across Sonnet 5, Haiku 4.5, GPT-5.6-sol and Gemini 3.7 Flash; `temperature` is ignored on two of those, so the harness cannot lean on it for determinism.
- Langfuse provides datasets, runs and scores, and the production traces already live there.

## Decision

- Cases are JSONL, one file per category, each with input turns, expected behaviour (answer facts, must-escalate flag, expected tool and argument constraints) and the KB section IDs the answer must ground on.
- Metrics: correctness (Haiku 4.5 judge, paraphrase-tolerant, given the expected facts); escalation correctness (binary: did the bot escalate exactly when it should); tool correctness (binary on tool name and argument constraints, qualification score included, ADR-0009); groundedness (each claim in the answer mapped by the judge to a cited KB section or flagged as unsupported).
- Runs: CI on every PR executes lint, unit tests and the stub-provider subset (deterministic, no key). The full suite runs locally or on demand against live models and writes one Langfuse dataset run per model.
- Human validation: the author reads and validates all 30 trap and tool cases by hand before relying on them; correctness cases are validated by sampling.
- The benchmark is this suite run per model, with cost and latency recorded from the response usage.
- The triage agent (ADR-0005) proposes new cases in the same JSONL shape; adding one is a PR.

## Considered Options

- RAGAS — lost because its retrieval metrics do not apply and its answer metrics duplicate a small judge behind an extra LLM configuration layer.
- DeepEval or promptfoo — lost because they duplicate pytest, already used for unit tests, and promptfoo adds a Node toolchain to a Python service.
- Langfuse-managed evaluators only — lost because they cannot gate CI; kept as Phase 2 for sampling production traces.
- Manual QA against the deployed app — lost because it is not repeatable and cannot drive a four-model benchmark.

## Consequences

- Positive: one toolchain; evals double as regression tests; the CI subset catches prompt and tool regressions without spending money; the same numbers appear in Langfuse next to production traces.
- Positive: binary metrics for the failure modes that matter make the benchmark comparable across vendors.
- Negative: the judge is non-deterministic; mitigated by preferring binary checks and re-running the judge where a score is close.
- Negative: single-turn cases dominate; multi-turn qualification flows are covered only by the 10 tool cases (Phase 2: scripted multi-turn conversations).
- Negative: live runs cost money and minutes and need a key, so they are not on every PR.
- Reopen when: retrieval is introduced (add retrieval metrics), production sampling is needed (Langfuse evaluators), or judge variance exceeds what binary checks absorb.

## Links

- Hallucination-trap inventory (what the site does not contain): [cadreai-site-facts](../research/cadreai-site-facts.md)
- Judge and target model prices, temperature and cache-minimum caveats: [openrouter-facts](../research/openrouter-facts.md), [claude-api-facts](../research/claude-api-facts.md)
- Related: [ADR-0001](0001-kb-in-prompt-no-rag.md), [ADR-0002](0002-openrouter-sole-provider.md), [ADR-0005](0005-event-driven-triage-agent.md), [ADR-0009](0009-bant-lite-qualification.md)
