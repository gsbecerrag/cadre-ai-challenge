# Eval reports

`make eval` and `make eval-report` write one JSON file per run here, named
`<UTC timestamp>-<model>.json`. The reports themselves are gitignored — they are the output of
a run, not a source file, and they carry whole Assistant answers — but the directory is kept so
a run never has to create it.

Each report is the shape the model benchmark (ticket 16) reads back, one file per model:

```json
{
  "model": "anthropic/claude-sonnet-5",
  "judge": "anthropic/claude-haiku-4.5",
  "started_at": "...", "finished_at": "...",
  "cost_usd": 0.0, "answer_cost_usd": 0.0, "judge_cost_usd": 0.0,
  "metrics": {
    "correctness": {"passed": 0, "ruled": 0, "failing": ["<eval case id>"]}
  },
  "cases": [
    {
      "id": "<eval case id>", "kind": "in_kb", "language": "en", "passed": true,
      "metrics": {"correctness": {"passed": true, "reason": "..."}},
      "answer": "...", "citations": [], "tools": [], "cost_usd": 0.0, "error": ""
    }
  ]
}
```
