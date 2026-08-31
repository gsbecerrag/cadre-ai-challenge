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
| Live-API load test | Measures the billing tier, not the design; a capacity model + stub-provider smoke test is the honest check ([architecture §capacity](docs/architecture.md)) | — |

## 4. Phases

Tickets are the unit of work (one branch, one PR, one TDD-driven subagent run each). The 19 tickets — 15 core, 3 optional, 1 honesty pass — live in [`.scratch/cadre-support-agent/issues/`](.scratch/cadre-support-agent/issues/) with their `Blocked by` edges and status; [`tasks.md`](.scratch/cadre-support-agent/tasks.md) is the generated index the subagent tooling reads.

| Phase | Tickets | Hours | Demoable outcome | Status |
|---|---|---|---|---|
| **P0 Foundations** | 01 scaffold + hello-world live on Cloud Run · strategy docs · super spec · tickets · credentials wizard | 1.5 | Public URL answers `/api/healthz`; docs reviewable | ✅ done — [PR #6](https://github.com/gsbecerrag/cadre-ai-challenge/pull/6) |
| **P1 Grounded chat** | 02 first Turn with the stub provider (seams, tool loop, SSE, KB compiler) · 03 real Grounded Answers (OpenRouter + Firestore Sessions) · 04 Knowledge Base + Escalation · 05 Refuse Set redaction · 06 Langfuse Traces · 07 demo Portal (parallel) | 2.5 | Ask about services/industries/Maturity Index → Grounded Answers with citations; Trap Questions escalate | 🟡 in progress — 02 ✅ [PR #9](https://github.com/gsbecerrag/cadre-ai-challenge/pull/9) · 03 ✅ [PR #11](https://github.com/gsbecerrag/cadre-ai-challenge/pull/11) · 04 ✅ [PR #10](https://github.com/gsbecerrag/cadre-ai-challenge/pull/10) · 07 ✅ [PR #8](https://github.com/gsbecerrag/cadre-ai-challenge/pull/8) |
| **P2 Leads & hand-over** | 08 Walkthrough Cards · 09 Lead capture + Qualification Score · 10 Strategist Console (Firebase Auth, Availability) · 11 Callback Hand-over + Console queue | 2 | A Qualified Lead appears in the Console the instant the Assistant creates it | ⚪ |
| **P3 Evals & CI** | 13 50 Eval Cases, four metrics, judge, Langfuse datasets; CI stub subset | 1.5 | `make eval` prints the scorecard; PRs run lint + unit + stub-provider evals | ⚪ |
| **P4 Feedback loop** | 12 thumbs → Langfuse score · 14 Triage Agent (Firebase Function) + Console Triage tab | 1.5 | Thumbs-down → Triage Report with a suggested KB fix, no human in the loop | ⚪ |
| **P5 Live video** | 15 Daily.co Live Hand-over, Strategist join/end, Availability gate, `LIVE_HANDOVER_ENABLED` | 2 | Visitor accepts → video call opens inside the chat; Strategist joins from the Console | ⚪ |
| **P6 If green** | 16 model benchmark · 17 capacity table + 200-VU stub smoke test · 18 in-app navigation · tldraw board | 3.5 | `docs/model-selection.md` with a real table | ⚪ optional |
| **P7 Honesty pass** | 19 cut log, README, demo script, final deploy | 1 | This file tells the truth | ⚪ |

**If forced to choose on Monday afternoon:** Triage Agent (P4) beats Live video (P5) — it's the better argument for the observability thesis, and Callback Hand-over still demos.

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

Model choice is asserted from priors today and **verified by a benchmark in P6** across four models via the same eval suite; until then Sonnet 5 is the working default for its cost/quality point and native prompt caching.

## 6. How the work is executed (the Claude Code workflow)

1. **Grilling session** (done 30 Aug) — 20 decisions, recorded as the [decision brief](docs/research/decision-brief-2026-08-30.md), then as ADRs. Facts were gathered by parallel research subagents ([docs/research/](docs/research/)).
2. **Super spec** via `/to-spec` — the conversation synthesised into one spec; test seams agreed before any code. **Design** in Claude Design from the spec and research: the chat widget, host page + Portal, and Strategist Console artboards are the visual spec for the UI tickets ([docs/design/](docs/design/README.md)); where they simplify the spec, the spec wins and the ruling is recorded.
3. **Tickets** via `/to-tickets` — vertical slices with explicit `Blocked by` edges; the frontier (unblocked tickets) is what runs next.
4. **Build** via subagent-driven development — per ticket: a fresh implementer subagent with **TDD required** (failing test shown before code), an independent reviewer subagent (spec compliance + quality), rulings ledgered and copied into `docs/process/`. File-disjoint tickets (demo Portal, KB authoring) run in parallel worktrees.
5. **One PR per ticket** with Conventional Commits; deploy from the laptop with `make deploy`; CI on PRs runs lint, unit tests, and the stub-provider eval subset (no API spend in CI).
6. **Downgrade rule:** if a ticket exceeds 2× its estimate or hits fix-round 3, the controller finishes it directly (still TDD, one code review) and logs the ruling here.

## 7. Cut log

| Date | Cut / change | Why |
|---|---|---|
| 2026-08-30 | Vector RAG, Bedrock, Firecrawl ingestion → Phase 2 | KB fits a cached prompt; site is static HTML |
| 2026-08-30 | Anthropic-direct provider → Phase 2 | Cadre supplied an OpenRouter key; one API for every model |
| 2026-08-30 | Slack/email notification → Phase 2 | No Slack workspace; Console realtime notification is enough for the demo |
| 2026-08-30 | RAGAS → pytest suite | No retrieval to score; kept the faithfulness idea as a groundedness metric |
| 2026-08-30 | Voice, in-page navigation on cadreai.com → out | No surface / no destination today |
| 2026-08-31 | Design's calendar picker and "Scheduled for" callback slot → Phase 2 | No scheduling concept in the spec; a Callback means a Strategist reaches out |
| 2026-08-31 | Design's qualification labels ("Decision authority", "Team size stated", …) → replaced by the spec's five signals | The score must be computable from `capture_lead` arguments ([ADR-0009](docs/adr/0009-bant-lite-qualification.md)) |

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
