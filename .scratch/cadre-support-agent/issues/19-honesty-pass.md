# 19: Honesty pass — cut log, README, demo script, final deploy check

**What to build:** The interviewer opens the repository and finds it truthful: plan.md's status and cut log reflect exactly what shipped, what was cut, and why; the README explains how to run, test, evaluate, and deploy in a few commands and links the plan, the spec, the architecture doc, and the ADRs; a demo script walks the spec's order (grounded answer with citation → Trap Question → Walkthrough Card into the Portal → Lead capture → Hand-over with the Strategist joining from a second screen → thumbs-down → Triage Report → the Trace in Langfuse → the eval scorecard); and the deployed URL passes a final smoke check of every shipped feature. Every ticket's Status matches reality. Phase P7.

**Blocked by:** 13 (Fifty Eval Cases, four metrics, and the CI stub subset), 14 (Triage Agent on thumbs-down and the Console Triage tab), 15 (Live Hand-over on video inside the chat) — or whichever of these were completed; anything not completed is recorded as cut in this ticket

**Status:** ready-for-agent

- [ ] plan.md: every phase row has a final status; every cut is in the cut log with a reason; the "if forced to choose" note reflects what actually happened.
- [ ] README: run, test, `make eval`, deploy, the public URL, and the document map; no stale command.
- [ ] Demo script committed with the exact prompts to type and what to point at on the second screen.
- [ ] Final smoke on the deployed URL: health, a cited answer, a Trap Question, a Walkthrough Card, a Lead, a Handover Request in the Console, a Feedback score in Langfuse, and (if shipped) a Triage Report and a video call; results recorded in the PR.
- [ ] All ticket files carry their final Status and a `## Comments` line with their PR.
