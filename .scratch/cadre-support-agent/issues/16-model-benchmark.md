# 16: Model benchmark across four models (optional)

**What to build:** A Cadre engineer runs the evaluation suite against four models through the same provider — Claude Sonnet 5, Claude Haiku 4.5, the current GPT-5.6 flagship, and the current Gemini Flash — and gets a comparison table of correctness, escalation correctness, tool correctness, groundedness, median time to first token, and cost per conversation; the table is published in the repository's model-selection document with the default model set from the evidence (Sonnet 5 stays unless clearly beaten). Optional; Phase P6.

**Blocked by:** 13 (Fifty Eval Cases, four metrics, and the CI stub subset)

**Status:** ready-for-agent

- [ ] `make benchmark` runs the suite once per configured model id and writes one JSON report per model plus a combined table.
- [ ] The model-selection document explains the method, the n=50 limitation, the cost of the run, and the decision; it links the ADR on the provider.
- [ ] The chosen default is reflected in configuration and, if it changed, in plan.md's cut log.
