# Plan — Cadre AI Support Agent

> Entry point for the review. Read this first, then the [super spec](.scratch/cadre-support-agent/spec.md) (product + engineering source of truth), then [docs/architecture.md](docs/architecture.md). Every scope change lands in the same PR as the code that causes it, so this file is always current.

**Deadline:** repo shared Mon 31 Aug 2026 (due Tue 1 Sep); live review Wed 2 Sep, 15:00 COT. **Budget:** ~12h core + ~3.5h optional, across Sun evening and Monday.

## 1. Goal

A customer-support **Assistant** for Cadre AI that a prospect or client can plausibly use today: it answers from a curated **Knowledge Base** with citations, refuses to invent what Cadre doesn't publish, qualifies **Leads**, and hands warm leads to a human **Strategist** — live, on video, inside the chat. Deployed on a public URL, observable end-to-end, and evaluated against 50 scenarios. Vocabulary: [CONTEXT.md](CONTEXT.md).

## 2. Hard deliverables

- [x] Public URL: <https://cadre-support-agent-495870119371.us-central1.run.app> (Cloud Run, us-central1) — hello-world live 31 Aug; features iterate against it
- [x] Code on GitHub with small PRs — [gsbecerrag/cadre-ai-challenge](https://github.com/gsbecerrag/cadre-ai-challenge), one PR per ticket (`main` moves only by PR — see [CLAUDE.md](CLAUDE.md))
- [x] `CLAUDE.md` at the root
- [x] `plan.md` at the root (this file)

## 3. Scope — what's in, what's out, and why

**In (the MVP triad — "3 working features beat 8 broken ones"):**

| # | Feature | Why this one |
|---|---|---|
| 1 | **Grounded Q&A + honest Escalation** — KB compiled into a prompt-cached system prompt with KB Section ids; **Trap Questions** (pricing, portal login URL, SOC 2, headcount…) are escalated, never answered | The brief's six scenarios and its "must not hallucinate" bar; the #1 way a support bot embarrasses a consultancy is inventing a fact it doesn't publish |
| 2 | **Lead qualification + Hand-over** — Qualification Score computed in code; Callback path first, then **Live Hand-over** on video (Daily.co) offered only when a Strategist is online | "How to book a call" has no destination on cadreai.com (every CTA is the contact form); keeping the lead warm *is* the product value |
| 3 | **Observability + quality loop** — Langfuse traces with cost per conversation, thumbs up/down, thumbs-down → independent **Triage Agent** → Triage Report in the Console; 50-case eval suite with four metrics | The interviewer's "how do you know it works, and how does it improve" — answered with data, not claims |

**Deliberately out (designed, drawn in the vision diagram, not built):**

| Cut | Why | Trigger to revisit |
|---|---|---|
| Vector RAG / admin document upload | KB is ~30 static pages ≈ 25K tokens; fits one cached prompt at ~1¢/turn with zero retrieval-miss risk ([ADR-0001](docs/adr/0001-kb-in-prompt-no-rag.md)) | KB > ~50 pages or non-engineers must edit it |
| Voice | Different product surface; no time | Product decision post-MVP |
| In-page navigation on cadreai.com | We don't own the site; no Portal exists today — Walkthrough Cards + a demo Portal instead | Real Portal exists |
| Agent framework (LangGraph/ADK) | Single Assistant, ~5 tools: a raw tool loop is fully explainable ([ADR-0004](docs/adr/0004-raw-tool-loop.md)) | Multi-agent or durable multi-step workflows |
| Slack/email notifications, HubSpot sync | Console gets the Handover Request in real time; no external service to fail on demo day | Strategists live in Slack/HubSpot |
| Cross-provider fallback, IP rate limiting, conversation summarisation, deploy-on-merge, Jitsi self-hosting | Each is one line in the architecture and a slide's worth of risk if untested | Stated per item in the spec |
| Live-API load test | Measures the billing tier, not the design; the honest check is a capacity model ([architecture §capacity](docs/architecture.md)). The stub-provider smoke test that would have measured the *app* layer under it (ticket 17) was cut too — see [§7](#7-cut-log) | — |

## 4. Phases

Tickets are the unit of work (one branch, one PR, one TDD-driven subagent run each). The 20 tickets — 15 core, 3 optional (all three cut), 1 honesty pass, 1 mid-build scope addition — live in [`.scratch/cadre-support-agent/issues/`](.scratch/cadre-support-agent/issues/) with their `Blocked by` edges and status; [`tasks.md`](.scratch/cadre-support-agent/tasks.md) is the generated index the subagent tooling reads.

| Phase | Tickets | Hours | Demoable outcome | Status |
|---|---|---|---|---|
| **P0 Foundations** | 01 scaffold + hello-world live on Cloud Run · strategy docs · super spec · tickets · credentials wizard | 1.5 | Public URL answers `/api/healthz`; docs reviewable | ✅ done — [PR #6](https://github.com/gsbecerrag/cadre-ai-challenge/pull/6) |
| **P1 Grounded chat** | 02 first Turn with the stub provider (seams, tool loop, SSE, KB compiler) · 03 real Grounded Answers (OpenRouter + Firestore Sessions) · 04 Knowledge Base + Escalation · 05 Refuse Set redaction · 06 Langfuse Traces · 07 demo Portal (parallel) | 2.5 | Ask about services/industries/Maturity Index → Grounded Answers with citations; Trap Questions escalate | ✅ done — [#9](https://github.com/gsbecerrag/cadre-ai-challenge/pull/9) · [#11](https://github.com/gsbecerrag/cadre-ai-challenge/pull/11) · [#10](https://github.com/gsbecerrag/cadre-ai-challenge/pull/10) · [#15](https://github.com/gsbecerrag/cadre-ai-challenge/pull/15) · [#19](https://github.com/gsbecerrag/cadre-ai-challenge/pull/19) · [#8](https://github.com/gsbecerrag/cadre-ai-challenge/pull/8) |
| **P2 Leads & hand-over** | 08 Walkthrough Cards · 09 Lead capture + Qualification Score · 10 Strategist Console (Firebase Auth, Availability) · 11 Callback Hand-over + Console queue | 2 | A Qualified Lead appears in the Console the instant the Assistant creates it | ✅ done — [#13](https://github.com/gsbecerrag/cadre-ai-challenge/pull/13) · [#14](https://github.com/gsbecerrag/cadre-ai-challenge/pull/14) · [#17](https://github.com/gsbecerrag/cadre-ai-challenge/pull/17) · [#22](https://github.com/gsbecerrag/cadre-ai-challenge/pull/22) |
| **P3 Evals & CI** | 13 50 Eval Cases, four metrics, judge, Langfuse datasets; CI stub subset | 1.5 | `make eval` prints the scorecard; PRs run lint + unit + stub-provider evals | ✅ done — [PR #18](https://github.com/gsbecerrag/cadre-ai-challenge/pull/18) |
| **P4 Feedback loop** | 12 thumbs → Langfuse score · 14 Triage Agent (Firebase Function) + Console Triage tab | 1.5 | Thumbs-down → Triage Report with a suggested KB fix, no human in the loop | ✅ done — [#23](https://github.com/gsbecerrag/cadre-ai-challenge/pull/23) · [PR #26](https://github.com/gsbecerrag/cadre-ai-challenge/pull/26) |
| **P5 Live video** | 15 Daily.co Live Hand-over, Strategist join/end, Availability gate, `LIVE_HANDOVER_ENABLED` | 2 | Visitor accepts → video call opens inside the chat; Strategist joins from the Console | ✅ done — [PR #24](https://github.com/gsbecerrag/cadre-ai-challenge/pull/24) |
| **P6 If green** | 16 model benchmark · 17 capacity table + 200-VU stub smoke test · 18 in-app navigation · tldraw board | 3.5 | `docs/model-selection.md` with a real table | ⛔ cut — 16, 17, 18 `wontfix`; the clock went to P4 and P5 instead. Reasons and consequences in [§7](#7-cut-log) |
| **P7 Honesty pass** | 19 cut log, README, demo script, final deploy | 1 | This file tells the truth | ✅ done — [PR #28](https://github.com/gsbecerrag/cadre-ai-challenge/pull/28) |
| **P8 Scope add (31 Aug)** | 20 Console email/password sign-in for reviewers without a Google account | 0.5 | The demo credentials sign in to the Console | ✅ done — [PR #25](https://github.com/gsbecerrag/cadre-ai-challenge/pull/25) |

**If forced to choose on Monday afternoon** the rule was: Triage Agent (P4) beats Live video (P5) — it's the better argument for the observability thesis, and Callback Hand-over still demos.

**What actually happened:** the choice never had to be made. Both landed on 31 Aug — Live video in [PR #24](https://github.com/gsbecerrag/cadre-ai-challenge/pull/24), the Triage Agent in [PR #26](https://github.com/gsbecerrag/cadre-ai-challenge/pull/26) — and the hour that bought them came out of P6, which is why all three optional tickets are `wontfix` rather than deferred-and-maybe. The demo therefore shows *both* Hand-over modes: video when a Strategist is Online, Callback when nobody is.

## 5. Key decisions (one line each; the reasoning is in the ADRs)

1. [KB in a cached prompt, no vector RAG](docs/adr/0001-kb-in-prompt-no-rag.md)
2. [OpenRouter is the sole runtime LLM provider; Sonnet 5 default, switch by env var](docs/adr/0002-openrouter-sole-provider.md)
3. [GCP lock-in accepted; portability lives in tested seams](docs/adr/0003-gcp-with-seams.md)
4. [Raw tool loop over an agent framework; LangGraph named for Phase 2](docs/adr/0004-raw-tool-loop.md)
5. [Triage Agent is event-driven and independent (Firestore trigger)](docs/adr/0005-event-driven-triage-agent.md)
6. [Two Redaction Profiles; Contact Details stay raw on the Lead](docs/adr/0006-two-profile-pii.md)
7. [Daily.co for Live Hand-over; Jitsi is the self-hosted vision](docs/adr/0007-daily-video-handover.md)
8. [pytest eval suite over RAGAS; groundedness judged against the KB](docs/adr/0008-pytest-evals-over-ragas.md)
9. [Qualification Score is computed in code from tool arguments](docs/adr/0009-bant-lite-qualification.md)
10. [Firebase Auth with an allowlist on the Console; Visitors stay anonymous](docs/adr/0010-firebase-auth-console.md)

**The default model is a reasoned choice, not a measured one.** The four-model benchmark (ticket 16) was cut with the rest of P6, so `make benchmark` and `docs/model-selection.md` do not exist: Sonnet 5 stands on its published cost/quality point, its native 1-hour prompt caching and its strict structured outputs ([ADR-0002](docs/adr/0002-openrouter-sole-provider.md)). The instrument that would settle it is already built and is the honest next step — the 50-case suite runs against any model id, and switching the default is one environment variable.

## 6. How the work is executed (the Claude Code workflow)

1. **Grilling session** (done 30 Aug) — 20 decisions, recorded as the [decision brief](docs/research/decision-brief-2026-08-30.md), then as ADRs. Facts were gathered by parallel research subagents ([docs/research/](docs/research/)).
2. **Super spec** via `/to-spec` — the conversation synthesised into one spec; test seams agreed before any code. **Design** in Claude Design from the spec and research: the chat widget, host page + Portal, and Strategist Console artboards are the visual spec for the UI tickets ([docs/design/](docs/design/README.md)); where they simplify the spec, the spec wins and the ruling is recorded.
3. **Tickets** via `/to-tickets` — vertical slices with explicit `Blocked by` edges; the frontier (unblocked tickets) is what runs next.
4. **Build** via subagent-driven development — per ticket: a fresh implementer subagent with **TDD required** (failing test shown before code), an independent reviewer subagent (spec compliance + quality), rulings ledgered and copied into `docs/process/`. File-disjoint tickets (demo Portal, KB authoring) run in parallel worktrees.
5. **One PR per ticket** with Conventional Commits; deploy from the laptop with `make deploy`; CI on PRs runs lint, unit tests, and the stub-provider eval subset (no API spend in CI).
6. **Downgrade rule:** if a ticket exceeds 2× its estimate or hits fix-round 3, the controller finishes it directly (still TDD, one code review) and logs the ruling here.

## 7. Cut log

This is the authority for what is *not* here. It records both scope cuts (something planned that was not built) and deliberate limits (something built to a knowingly shorter edge). The README's "Honest limits" section is the reader-facing summary of the second half; where the two differ, this table wins.

| Date | Cut / change | Why |
|---|---|---|
| 2026-08-30 | Vector RAG, Bedrock, Firecrawl ingestion → Phase 2 | KB fits a cached prompt; site is static HTML |
| 2026-08-30 | Anthropic-direct provider → Phase 2 | Cadre supplied an OpenRouter key; one API for every model |
| 2026-08-30 | Slack/email notification → Phase 2 | No Slack workspace; Console realtime notification is enough for the demo |
| 2026-08-30 | RAGAS → pytest suite | No retrieval to score; kept the faithfulness idea as a groundedness metric |
| 2026-08-30 | Voice, in-page navigation on cadreai.com → out | No surface / no destination today |
| 2026-08-30 | **Names and street addresses are not redacted** from Traces or the store → Phase 2 ([ADR-0006](docs/adr/0006-two-profile-pii.md)) | The `refuse` profile keeps cards, bank details, government ids and credentials out of the model, the store and the logs; the `full` profile tokenises emails and phones on the way to Langfuse. Names need a model pass, and a regex that tried would damage Contact Details — the data the product exists to collect |
| 2026-08-31 | Design's calendar picker and "Scheduled for" callback slot → Phase 2 | No scheduling concept in the spec; a Callback means a Strategist reaches out |
| 2026-08-31 | Design's qualification labels ("Decision authority", "Team size stated", …) → replaced by the spec's five signals | The score must be computable from `capture_lead` arguments ([ADR-0009](docs/adr/0009-bant-lite-qualification.md)) |
| 2026-08-31 | Scope ADDITION: Console email/password sign-in (ticket 20), shipped in [PR #25](https://github.com/gsbecerrag/cadre-ai-challenge/pull/25) | A reviewer may not have a Google account; a demo account with test credentials in Secret Manager is shareable without one. The only addition to scope after the tickets were cut |
| 2026-08-31 | Ticket 16, the four-model benchmark → `wontfix` | Deadline. The consequence is stated in §5: the default model is reasoned, not measured. The eval suite that would measure it exists and takes one env var to point at another model |
| 2026-08-31 | Ticket 17, the 200-VU stub-provider smoke test → `wontfix` | Deadline. The consequence: [architecture §8](docs/architecture.md)'s capacity table is a *model* — arithmetic from the provider's rate-limit tier and Cloud Run's concurrency setting — not a measurement. The binding constraint it identifies (the OpenRouter tier, not this app) is a design fact and does not depend on the missing run |
| 2026-08-31 | Ticket 18, in-app navigation from a Walkthrough Card → `wontfix` | Deadline, and it is the least load-bearing of the three: a Walkthrough Card already opens the Portal page with the chat still open. What is missing is the SPA navigating and pulsing the target element |
| 2026-08-31 | The tldraw vision board (P6) → `wontfix` | The vision diagram in [architecture §6](docs/architecture.md) already carries the Phase-2 picture; a second rendering of it is presentation polish |
| 2026-08-31 | Langfuse **dataset-run upload** → an empty seam (`evals/sink.py`) | langfuse 4.15 removed `dataset_item.link`, and wiring its replacement blind on deadline day was worse than a seam with nothing behind it. Traces, Feedback scores and Triage comments **are** live in Langfuse; only the eval-run-as-dataset-run is missing, and `make eval` writes the same numbers to a local JSON report |
| 2026-08-31 | No Firestore **TTL policy on `sessions`** → Phase 2 | Parked from ticket 03. A Session ends politely after `MAX_TURNS_PER_SESSION` (40) Turns, but the documents stay forever. A TTL policy is project configuration rather than code, so it changes nothing about the design and nothing in the demo depends on it |
| 2026-08-31 | **Feedback stays keyed by the Langfuse Trace id** → Phase 2 | One id was cheaper than two while Langfuse is the only consumer of a score. The visible cost: with no Langfuse keys configured a Turn has no Trace id, so the thumbs do not render and the Triage Agent has nothing to fire on |
| 2026-08-31 | **The eval scorecard was not re-run** after ticket 11's fixes | The last full run (ticket 13: correctness 19/20 · groundedness 44/50 · escalation 20/20 · tool 6/10) found two `tool_correctness` causes, and ticket 11 fixed both. Re-running costs ~$0.60 and several minutes of the same OpenRouter credit the live demo needs, so 6/10 is quoted as a floor rather than refreshed |
| 2026-08-31 | **Secret copies do not auto-rotate** | A Firebase Function binds Secret Manager ids as environment variable *names*, so it cannot name `openrouter-api-key`. `deploy-secrets` keeps `OPENROUTER_API_KEY` / `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` as copies of the hyphenated originals; adding a version to one does not update the other, so rotation adds a version to both |
| 2026-08-31 | **One Strategist identity for the demo** | The allowlist holds one real Google address and the demo account, and Availability is one presence document per signed-in identity — two people signed in as the demo account share one Availability toggle. Multi-Strategist routing was never in scope; the Console shows a queue, not an assignment engine |
| 2026-08-31 | **An abandoned Handover Request times out lazily** | A Visitor who closes the tab mid-call leaves the request open until the widget's next status poll or the Strategist's "End call". A server-side sweeper is a scheduled Function — the same pattern as the Triage Agent — and was not worth a second Function before the review |
| 2026-08-31 | **Single region, single provider, no fallback** | Cloud Run `us-central1`, Firestore `nam5`, OpenRouter with no cross-provider failover. Multi-region is a deploy-topology change with nothing to demonstrate; OpenRouter's `models: [...]` fallback is one line and stays a Phase-2 line because an untested failover path is a worse demo-day risk than a tested single path |
| 2026-08-31 | **One timing-sensitive test is left in** | `core/tests/test_redaction.py`'s spoken-dots case asserts a wall-clock bound on the redactor. It guards a real request-path DoS (54 s before the fix, 2.7 ms after), and a loaded CI runner can still push it over its margin. Replacing wall-clock with an operation count was the right fix and did not fit the day; re-run it if it flakes |
| 2026-08-31 | **The two-device video recording and the signed-in Console screenshots are the operator's**, not automated | Both need a second screen with a Strategist's Firebase session; no browser driver is in the loop and a headless run cannot hold that session. Everything reachable without one — including the signed-out Console's 401s and the Firestore rules denials — is recorded in [docs/transcripts/](docs/transcripts/) |

## 8. Risks and fallbacks

| Risk | Fallback |
|---|---|
| Cloud Run deploy blocked | Ticket 01 is hello-world deploy; nothing else starts until the URL is live |
| Firebase Functions (Python) packaging | `make deploy-functions` copies `core/`; fallback is a FastAPI background task, recorded in ADR-0005 |
| Daily.co / Google sign-in config | `LIVE_HANDOVER_ENABLED=false` keeps the demo on the Callback path; Console falls back to a shared token |
| Subagent review loops eat hours | Cap 2 fix rounds; downgrade rule above |

## 9. Document map

| Path | What |
|---|---|
| [CLAUDE.md](CLAUDE.md) | How Claude Code works in this repo: commands, conventions, process rules |
| [CONTEXT.md](CONTEXT.md) | Glossary — the words code, docs, and tests must share |
| [.scratch/cadre-support-agent/spec.md](.scratch/cadre-support-agent/spec.md) | Super spec (PRD + engineering decisions + test seams) |
| [.scratch/cadre-support-agent/issues/](.scratch/cadre-support-agent/issues/) | Tickets, with status and blocking edges |
| [docs/architecture.md](docs/architecture.md) | Diagrams, tech-stack table, data model, capacity model |
| [docs/adr/](docs/adr/) | The ten decision records |
| [docs/research/](docs/research/) | Evidence: cadreai.com facts, OpenRouter and Claude API facts, decision brief |
| [docs/design/](docs/design/README.md) | Claude Design artboards (chat widget, mock site + Portal, Strategist Console), the design brief, and the spec-vs-design rulings |
| [docs/agents/](docs/agents/) | Conventions for the engineering skills (issue tracker, triage labels, domain docs) |
| [.claude/skills/](.claude/skills/) | Project skills: `pii-redaction` (adapted for B2B), `mvp-prioritization` |
