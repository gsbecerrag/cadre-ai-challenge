# 13: Fifty Eval Cases, four metrics, and the CI stub subset

**What to build:** A Cadre engineer runs `make eval` and gets a scorecard: correctness on in-KB questions, escalation correctness on Trap Questions, tool correctness on qualification scenarios, and groundedness of every answer against the Knowledge Base — over fifty Eval Cases in one JSONL file (about twenty in-KB with golden answers and expected section ids, about twenty Trap Questions including three or four prompt-injection variants, about ten qualification cases with expected tool calls, arguments, and score). The judge is a cheaper model behind the same provider seam; results are recorded as a dataset run in Langfuse when keys are present. The deterministic subset (escalation and tool cases) runs in CI against the stub provider so pull requests catch regressions with no API spend. Golden answers are drafted from the Knowledge Base; the Trap and qualification cases are hand-validated by the author before they count. Phase P3.

**Blocked by:** 04 (Complete Knowledge Base and honest Escalation on Trap Questions), 09 (Lead capture with a Qualification Score computed in code)

**Status:** ready-for-agent

- [ ] The suite runs under its own pytest marker; the stub subset passes in CI without any external key; the full run requires the provider key and is skipped otherwise.
- [ ] Each metric is a function of the Eval Case and the Assistant's Turn result: escalation and tool metrics are deterministic; correctness and groundedness use the judge and tolerate paraphrase; covered at seam S5 with a stub judge for the metric logic itself.
- [ ] The scorecard prints per-metric pass rates and the failing case ids; a JSON report is written for the benchmark ticket to reuse.
- [ ] Results upload to Langfuse as a dataset run when configured, and the run is skipped cleanly otherwise.
- [ ] The full run against the real provider is executed once and its scorecard is pasted into the PR; the 30 hand-validated cases are marked as such in the JSONL.
