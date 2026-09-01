# 16: Model benchmark across four models (optional)

**What to build:** A Cadre engineer runs the evaluation suite against four models through the same provider — Claude Sonnet 5, Claude Haiku 4.5, the current GPT-5.6 flagship, and the current Gemini Flash — and gets a comparison table of correctness, escalation correctness, tool correctness, groundedness, median time to first token, and cost per conversation; the table is published in the repository's model-selection document with the default model set from the evidence (Sonnet 5 stays unless clearly beaten). Optional; Phase P6.

**Blocked by:** 13 (Fifty Eval Cases, four metrics, and the CI stub subset)

**Status:** wontfix

- [ ] `make benchmark` runs the suite once per configured model id and writes one JSON report per model plus a combined table.
- [ ] The model-selection document explains the method, the n=50 limitation, the cost of the run, and the decision; it links the ADR on the provider.
- [ ] The chosen default is reflected in configuration and, if it changed, in plan.md's cut log.

## Comments

- 2026-08-31 — wontfix (ticket 19, [PR #28](https://github.com/gsbecerrag/cadre-ai-challenge/pull/28)): Deadline: the hour went to P4 (Triage Agent) and P5 (Live video) instead. Consequence recorded in plan.md §5 and §7: the default model is a reasoned choice, not a measured one; the 50-case eval suite runs against any model id when the benchmark is wanted.
