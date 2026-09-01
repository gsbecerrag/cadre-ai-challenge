# 17: Capacity table and stub-provider concurrency smoke test (optional)

**What to build:** A Cadre engineer can point a load script at a locally running Assistant configured with the stub provider and drive a couple of hundred concurrent streaming conversations, proving the app layer is stateless and streams under concurrency; the measured numbers (concurrent streams sustained, p50/p95 time to first event, error rate) go into the architecture document's capacity section next to the provider-tier formula. No live-API load test is run. Optional; Phase P6.

**Blocked by:** 03 (Real Grounded Answers on the public URL)

**Status:** wontfix

- [ ] A load script (Locust or k6) runs 200 virtual users against the chat endpoint with the stub provider and reports the metrics above.
- [ ] The architecture document's capacity section gains a "measured" row with the numbers and the command used.
- [ ] Any app-layer defect found (blocking call, unbounded memory) is fixed in this ticket with a test at seam S1 where possible.

## Comments

- 2026-08-31 — wontfix (ticket 19, [PR #28](https://github.com/gsbecerrag/cadre-ai-challenge/pull/28)): Deadline. Consequence recorded in plan.md §7: the capacity table in architecture §8 is a model, not a measurement; the binding constraint it identifies (the provider's rate-limit tier) does not depend on the missing run.
