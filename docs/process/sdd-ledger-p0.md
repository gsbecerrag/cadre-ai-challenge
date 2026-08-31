# SDD ledger — plan: .scratch/cadre-support-agent/tasks.md
Spec: .scratch/cadre-support-agent/spec.md (binding authority). Constraints: .scratch/cadre-support-agent/global-constraints.md.
Execution mode: one ticket = one worktree/branch (feat/NN-slug) = one PR; task review is the merge gate per ticket; finishing-a-development-branch runs per ticket. Ruling: the whole-branch final review collapses into the task review for single-task branches — why: each branch holds exactly one task; what it costs if wrong: a cross-task defect is caught one PR later by the next task review.
Fix-round cap for MVP tickets: 2 (not 5) — Ruling: cap 2 for tickets 01-15 — why: two-day deadline, plan.md risk table — what it costs if wrong: a contestable finding gets parked earlier than the skill's default.

## Pre-flight scan (tasks sharing files/interfaces)
| Tasks | Produces vs consumes | Finding / Ruling |
|---|---|---|
| 01 ↔ all | scaffold layout, Makefile targets, logging + config module | consistent; 01 defines the package layout the rest assume |
| 01 ↔ 06 | 01: "missing required variable fails fast"; 06: "app starts without Langfuse keys" | Ruling: only variables the selected providers need are required (e.g. OpenRouter key only when MODEL_PROVIDER=openrouter); integrations degrade to no-op when unconfigured — cost if wrong: a misconfigured deploy fails later instead of at boot |
| 02 ↔ 03 | 02 defines ModelProvider/ConversationStore + stub/memory impls; 03 adds openrouter/firestore impls | consistent; 02 must define the interfaces with the fields 03 needs (usage incl. cost, cache marker, typed provider error) — carried into 02's dispatch |
| 02 ↔ 03 | 02 needs a Session for S1 tests; 03 "Sessions become anonymous cookie" | Ruling: 02 introduces the session id + HTTP-only cookie minimally; 03 hardens it (turn cap, Firestore) — cost if wrong: small rework in 03 |
| 02 ↔ 06 | 02: done event carries Trace id + usage; tracing exists only from 06 | Ruling: 02 emits usage and a null/absent trace id; 06 fills it — cost: none |
| 02 ↔ 05 | 05 hooks refuse-profile redaction before provider call and before store write | 02 must expose a single pre-model/pre-store point in the turn pipeline — carried into 02's dispatch |
| 03 ↔ 06 | cost from OpenRouter usage chunk → Trace | consistent |
| 05 ↔ 06 | full profile applied to trace I/O | consistent |
| 07 ↔ 08/18 | Portal routes + element ids consumed by walkthrough catalogue | 07 must publish stable route names and element ids — in 07's criteria |
| 09 ↔ 10/11 | leads collection + score read by Console; offer gating reads score | consistent |
| 10 ↔ 11/14 | Console shell, allowlist auth, realtime listeners reused | consistent |
| 11 ↔ 15 | state machine defined in 11 incl. video-only states; 15 implements video transitions | consistent; 11 must include the full state set from the spec — in 11's criteria |
| 12 ↔ 14 | feedback doc shape (session id, trace id, rating) consumed by the trigger | consistent |
| 04 ↔ 13 | KB section ids referenced by golden answers | 13 must be authored against 04's final ids — sequencing already enforced by Blocked-by |
| each task | tests specified vs code specified | consistent: every criterion names its seam; no task mandates an assertion-free test or duplicated logic |
Scan verdict: no contradictions with the Global Constraints; three rulings above carried into dispatches.

## Progress
Task 1: dispatched — BASE 554e2f00, implementer model opus, brief .superpowers/sdd/tasks/task-1-brief.md, report task-1-report.md, branch feat/01-hello-world-live-on-cloud-run (worktree .claude/worktrees/feat+01-hello-world-live-on-cloud-run)
Task 1: report DONE_WITH_CONCERNS — 10 commits 554e2f0..ff85fe6, 29 pytest + 2 vitest green, make check clean; deployed https://cadre-support-agent-495870119371.us-central1.run.app; report .superpowers/sdd/tasks/task-1-report.md
Task 1: Ruling: canonical health path is /api/healthz; /healthz stays in-app as a local/docker alias — why: controller verified GFE answers /healthz on *.run.app with a 404 that never reaches the container, while /api/healthz returns the JSON body — what it costs if wrong: one redundant route
Task 1: Ruling: CI "never ran" is not a gap — it runs on this ticket's PR; the PR must show it green before merge — cost if wrong: none
Task 1: carry-forward → Task 3: make deploy must switch from --set-env-vars to --update-env-vars/--set-secrets when the OpenRouter secret is bound
Task 1: review package .superpowers/sdd/tasks/review-554e2f0..ff85fe6.diff; reviewer model opus dispatched
Task 1: ticket 01 Status → in-progress committed (117343e); Claude Design import pending user /design-login (DesignSync refused: no design-system authorization in this non-interactive session)
Task 1: review — Spec ✅ (7/7 verifiable criteria mapped; ⚠️ deployed /healthz → ruled /api/healthz canonical; ⚠️ CI unrun → PR; ⚠️ browser check → controller curl 200 html), quality Approved, 2 Important, 7 Minor
Task 1: minor (deferred): core/config.py get_settings() is dead code — delete or wire create_app through it
Task 1: minor (deferred): Settings.port never read by production code (Dockerfile uses shell ${PORT}, make dev hard-codes 8080)
Task 1: minor (deferred): .env.example lacks SERVICE_NAME though core/config.py reads it
Task 1: minor (deferred): api/middleware.py logs failed requests (status 500) at INFO — choose severity from status
Task 1: minor (deferred, load-bearing for JSON-log contract): core/logging.py leaves the root logger unmanaged — third-party loggers fall to lastResort plain text; carry into Task 2 (first ticket adding SDK-style dependencies)
Task 1: minor (deferred): Dockerfile bakes api/tests and core/tests into the runtime image — add **/tests/** to .dockerignore; carry into Task 3 (next deploy-touching ticket)
Task 1: minor (deferred): web/src/App.test.tsx has two tests vs the "one web smoke test" budget — accepted; second covers an acceptance criterion
Task 1: fix round 1/2 dispatched — findings: (a) api/web.py SPA fallback returns 200 shell for unknown /api/* (guard + S1 test for GET /api/not-a-route → 404); (b) test_the_servers_plain_text_access_log_is_silenced has no RED — document vacuous RED and prove it fails when silencing is removed. FIX_BASE 117343e (ff85fe6 + controller bookkeeping commit 117343e)
Task 1: fix round 1/2 — implementer DONE: 89419b0 fix(api) 404 for unknown /api/*, eddbf16 test(core) access-log RED established; 30 pytest + 2 vitest green, make check clean; not redeployed (controller will deploy from main after merge). Scoped re-review dispatched (sonnet) on review-117343e..eddbf16.diff
Task 1: fix round 1/2 (2 addressed, 0 open — /api/* 404 guard; access-log RED established; commits 117343e..eddbf16); re-review clean
Task 1: minor (deferred): bare GET /api (no trailing segment) still falls through to the SPA shell — mirrors the accepted /assets convention; fold into ticket 02 when the chat route lands
Task 1: complete (commits 554e2f0..eddbf16, review clean after 1 fix round)
