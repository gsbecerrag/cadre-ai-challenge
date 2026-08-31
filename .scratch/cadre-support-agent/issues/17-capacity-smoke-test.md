# 17: Capacity table and stub-provider concurrency smoke test (optional)

**What to build:** A Cadre engineer can point a load script at a locally running Assistant configured with the stub provider and drive a couple of hundred concurrent streaming conversations, proving the app layer is stateless and streams under concurrency; the measured numbers (concurrent streams sustained, p50/p95 time to first event, error rate) go into the architecture document's capacity section next to the provider-tier formula. No live-API load test is run. Optional; Phase P6.

**Blocked by:** 03 (Real Grounded Answers on the public URL)

**Status:** ready-for-agent

- [ ] A load script (Locust or k6) runs 200 virtual users against the chat endpoint with the stub provider and reports the metrics above.
- [ ] The architecture document's capacity section gains a "measured" row with the numbers and the command used.
- [ ] Any app-layer defect found (blocking call, unbounded memory) is fixed in this ticket with a test at seam S1 where possible.
