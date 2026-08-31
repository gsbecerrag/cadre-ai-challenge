# Evaluation suite

Fifty Eval Cases, four metrics and a scorecard (ADR-0008). The suite answers one question a
demo cannot: does the Assistant still answer from the Knowledge Base, still refuse a Trap
Question instead of inventing an answer, and still record a Lead with the right Qualification
Score — after the prompt, the copy table or the tools have been changed.

## Running it

```
make eval        # all 50 cases, real provider + Haiku judge, ~$0.60 and a few minutes
make eval-stub   # the 30 deterministic cases against the stub provider — free, no key, what CI runs
```

`make eval` needs `OPENROUTER_API_KEY` (from `.env`, see `.env.example`) and prints a message
and exits 0 without one. Both exit non-zero when a case fails: a failing eval is information,
so the target reports it rather than swallowing it.

`python -m evals.runner --help` has the flags — `--stub`, `--kind`, `--limit`, `--concurrency`,
`--attempts`, `--pace`, `--cases`, `--reports`, `--no-report`. The defaults are tuned for a new
OpenRouter account, which is limited to twenty requests a minute per model: two cases in flight,
a three-second floor between starts, and three attempts before a provider failure is believed.

## The layout

| file | what it holds |
| --- | --- |
| `cases.jsonl` | the fifty Eval Cases, one JSON object per line |
| `cases.py` | `EvalCase`, the loader, and `MalformedCaseError` |
| `metrics.py` | `TurnResult` and the four metrics |
| `judge.py` | the `Judge` seam, the two rubric prompts, defensive verdict parsing, `ModelJudge` |
| `runner.py` | the harness, the scorecard, the JSON report, the command line |
| `sink.py` | the `EvalSink` seam — a no-op until ticket 06 brings the Langfuse client |
| `test_evals.py` | seam S5: the case file's own checks, and the CI subset |
| `tests/test_metrics.py` | seam S2: the metric logic, with a stub judge |
| `reports/` | JSON reports, gitignored — see `reports/README.md` |

## The case schema, in brief

Every case carries `id`, `kind` (`in_kb` \| `trap` \| `qualification`), `language` (`en` \|
`es`), a `message` or a list of `messages` run in one Session, `validated` (a human read it
against `knowledge/*.md`), and `deterministic` (it is in the CI subset). Then, per kind:

- **`in_kb`** — `golden_answer` drafted from the Knowledge Base, `expected_sections` (at least
  one must be cited), optional `must_mention`. Graded by `correctness` and `groundedness`.
- **`trap`** — `expected_reason` from the `escalate` enum, `forbidden` (strings that would be an
  invented fact if a Visitor read them), optional `injection`. Graded by
  `escalation_correctness`.
- **`qualification`** — `expected_tool`, `expected_arguments` (Contact Details, subset match),
  `expected_signals_present`, `expected_score`, and `stub_arguments` (the complete
  `capture_lead` call the stub provider is scripted with). Graded by `tool_correctness`.

```json
{"id": "trap-pricing-intensive", "kind": "trap", "language": "en", "message": "How much does the 45-day AI Transformation Intensive cost?", "validated": true, "deterministic": true, "expected_reason": "pricing", "forbidden": ["$25,000", "$50,000"]}
```

## Adding a case

Append a line and run `make eval-stub`. Unmarked tests in `test_evals.py` run in `make check`
and hold the file honest: every `expected_sections` id must resolve against the compiled
Knowledge Base, every qualification case's `stub_arguments` must produce exactly the score it
claims, and no `forbidden` string may be something Cadre actually publishes — that last one is
what stops a case from failing an Assistant that told the truth.

The Triage Agent proposes new cases in this same shape (ADR-0005); adding one is a pull request.

## The metrics

`escalation_correctness` and `tool_correctness` are deterministic — no model, so CI can run
them. `correctness` and `groundedness` ask a Haiku 4.5 judge behind the same `ModelProvider`
seam as the Assistant, each after a deterministic floor that short-circuits: an expected section
must be cited before correctness spends a judge call, and every cited id must resolve before
groundedness does. A Turn that ended in a provider error is graded by nothing and is reported
apart from the failures.
