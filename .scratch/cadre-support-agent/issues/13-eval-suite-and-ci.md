# 13: Fifty Eval Cases, four metrics, and the CI stub subset

**What to build:** A Cadre engineer runs `make eval` and gets a scorecard: correctness on in-KB questions, escalation correctness on Trap Questions, tool correctness on qualification scenarios, and groundedness of every answer against the Knowledge Base — over fifty Eval Cases in one JSONL file (about twenty in-KB with golden answers and expected section ids, about twenty Trap Questions including three or four prompt-injection variants, about ten qualification cases with expected tool calls, arguments, and score). The judge is a cheaper model behind the same provider seam; results are recorded as a dataset run in Langfuse when keys are present. The deterministic subset (escalation and tool cases) runs in CI against the stub provider so pull requests catch regressions with no API spend. Golden answers are drafted from the Knowledge Base; the Trap and qualification cases are hand-validated by the author before they count. Phase P3.

**Blocked by:** 04 (Complete Knowledge Base and honest Escalation on Trap Questions), 09 (Lead capture with a Qualification Score computed in code)

**Status:** done

- [x] The suite runs under its own pytest marker; the stub subset passes in CI without any external key; the full run requires the provider key and is skipped otherwise.
- [x] Each metric is a function of the Eval Case and the Assistant's Turn result: escalation and tool metrics are deterministic; correctness and groundedness use the judge and tolerate paraphrase; covered at seam S5 with a stub judge for the metric logic itself.
- [x] The scorecard prints per-metric pass rates and the failing case ids; a JSON report is written for the benchmark ticket to reuse.
- [x] Results upload to Langfuse as a dataset run when configured, and the run is skipped cleanly otherwise.
- [x] The full run against the real provider is executed once and its scorecard is pasted into the PR; the 30 hand-validated cases are marked as such in the JSONL.

## Comments

- Delivered in [PR #18](https://github.com/gsbecerrag/cadre-ai-challenge/pull/18). Reviewer: Approved — case fidelity, forbidden lists, keyless stub subset, and the on-disk report verified; one Important (an errored Turn could score a free pass) and minors fixed in round 1; scoped re-review: all addressed, no new breakage.
- Full run (Claude Sonnet 5 answers, Haiku 4.5 judge, $0.60): correctness 19/20 · groundedness 44/50 · escalation_correctness 20/20 · tool_correctness 6/10. Findings carried to ticket 11: `company_size_or_role` never captured when the title lands in the `role` Contact Detail; earlier-Turn signals dropped from a later `capture_lead`; the pricing Escalation copy lacks the KB's "event ticket" qualifier.
- Ruling: the Langfuse dataset-run upload is an `EvalSink` stub until ticket 06's client exists; ticket 12 wires it. The stub subset scripts the provider from each case, so it guards the copy table, the score, the events, and the prompt/enum lockstep — not the model.
- Ruling: cases were validated against `knowledge/*.md` by the implementer and re-traced by the reviewer; Galo spot-checks at review time. Parked: Spanish filler spellings in the score; no refusal metric for prompt-injection cases; `runner.py` split.
