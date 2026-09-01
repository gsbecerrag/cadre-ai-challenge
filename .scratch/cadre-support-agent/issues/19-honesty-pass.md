# 19: Honesty pass — cut log, README, demo script, final deploy check

**What to build:** The interviewer opens the repository and finds it truthful: plan.md's status and cut log reflect exactly what shipped, what was cut, and why; the README explains how to run, test, evaluate, and deploy in a few commands and links the plan, the spec, the architecture doc, and the ADRs; a demo script walks the spec's order (grounded answer with citation → Trap Question → Walkthrough Card into the Portal → Lead capture → Hand-over with the Strategist joining from a second screen → thumbs-down → Triage Report → the Trace in Langfuse → the eval scorecard); and the deployed URL passes a final smoke check of every shipped feature. Every ticket's Status matches reality. Phase P7.

**Blocked by:** 13 (Fifty Eval Cases, four metrics, and the CI stub subset), 14 (Triage Agent on thumbs-down and the Console Triage tab), 15 (Live Hand-over on video inside the chat) — or whichever of these were completed; anything not completed is recorded as cut in this ticket

**Status:** done

- [x] plan.md: every phase row has a final status; every cut is in the cut log with a reason; the "if forced to choose" note reflects what actually happened.
- [x] README: run, test, `make eval`, deploy, the public URL, and the document map; no stale command.
- [x] Demo script committed with the exact prompts to type and what to point at on the second screen.
- [x] Final smoke on the deployed URL: health, a cited answer, a Trap Question, a Walkthrough Card, a Lead, a Handover Request in the Console, a Feedback score in Langfuse, and (if shipped) a Triage Report and a video call; results recorded in the PR.
- [x] All ticket files carry their final Status and a `## Comments` line with their PR.

## Comments

- 2026-08-31 — done in [PR #28](https://github.com/gsbecerrag/cadre-ai-challenge/pull/28). Scope added mid-ticket at the operator's request: the README carries the demo prompts, the local-environment setup and the key-swap runbook, and `make rotate-openrouter-key` / `make check-openrouter-key` are the failsafe for a dead OpenRouter key. The final smoke on the deployed revision (e619c71 — unchanged by this docs-only PR) is recorded in the PR body; the two-device video recording and the signed-in Console screenshots stay the operator's.
