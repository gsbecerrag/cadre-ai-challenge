# Cadre AI Support Agent

A customer-support **Assistant** for [Cadre AI](https://www.cadreai.com), an AI strategy and
implementation consultancy. A prospect or an existing client asks it what Cadre does, which
industries it serves, what the AI Maturity Index is, how the Portal works, how Cadre picks
models and protects data — and it answers **only from a curated Knowledge Base, citing the
section every claim came from**. When Cadre does not publish the answer (pricing, a Portal
login URL, SOC 2, headcount) it says so and gives a real next step instead of inventing one.
Along the way it qualifies a **Lead** and hands a warm one to a human **Strategist** — live on
video inside the chat, or as a Callback.

This repository is the take-home for a Director of AI Engineering role at Cadre AI. The brief
is [`Cadre_AI_Chatbot_Take_Home_Candidate.docx.md`](Cadre_AI_Chatbot_Take_Home_Candidate.docx.md);
the plan that drove the build is [`plan.md`](plan.md).

**Live:** <https://cadre-support-agent-495870119371.us-central1.run.app>

## Two minutes on the live app

Open the URL. It renders a mock cadreai.com host page with the Assistant docked bottom-right
(the widget is the product; the page under it is scenery).

1. **A grounded answer.** "What does Cadre AI do, and which industries do you work with?" —
   the answer streams, and every claim carries a `[topic#heading]` citation chip you can tap
   to read the Knowledge Base section it came from.
2. **A trap question.** "How much does the 45-day AI Transformation Intensive cost?" — no
   number is invented. You get an Escalation card: what Cadre *does* publish (the one price it
   publishes is the $5,000 PE Playbook), what cannot be confirmed, and one concrete next step.
   Also try "What's the Portal login URL?", "Are you SOC 2 certified?", "How do you compare to
   Accenture?".
3. **A walkthrough into the Portal.** "How do I see my agents' results in the portal?" — a
   Walkthrough Card with steps and a button that opens the demo Portal at
   [`/portal/agents`](https://cadre-support-agent-495870119371.us-central1.run.app/portal/agents)
   with the results panel in view, chat still open. The Portal is mock data and says so.
4. **Lead capture and hand-over.** Share a name, a work email, a company and a problem
   ("I'm Jane Doe, VP of Operations at Acme Manufacturing, jane@example.com — supplier
   paperwork eats three days a week and we want to fix it this quarter"). A Qualification
   Score is computed in code from five signals; at three or more, the Assistant offers a
   hand-over exactly once.
5. **The Console.** [`/console`](https://cadre-support-agent-495870119371.us-central1.run.app/console)
   is the Strategist side: Availability, the Handover queue, Callbacks, and Triage. Sign in
   with **Google** if your address is on the allowlist, or with the **email/password demo
   credentials** — the account is `strategist@cadre-demo.example` and the password is held in
   Secret Manager; ask the operator for it (it is deliberately not in this repository).
6. **The quality loop.** Give an answer a thumbs-down. The rating becomes a score on that
   Turn's Langfuse Trace, and an independent Triage Agent (a Firebase Function on the Firestore
   write) posts a **Triage Report** — category, evidence, a suggested Knowledge Base addition
   and a suggested Eval Case — into the Console's Triage tab in about twenty seconds.

Personal data note: it is a live demo on a real project. Use obviously fake details.

## Architecture in a paragraph

**One Cloud Run container** serves the FastAPI API and the built React SPA from the same origin
— no CORS, one deploy ([ADR-0003](docs/adr/0003-gcp-with-seams.md)). `POST /api/chat` answers
`text/event-stream`; `core/turn.py` is the entire agent loop — load the Session from the
`ConversationStore`, redact the Visitor message once at a single pre-model/pre-store hook,
assemble the prompt with the byte-stable Knowledge Base block first so it hits the Anthropic
prompt cache, call the `ModelProvider` with the tool definitions, run tool calls in code, feed
results back, at most four iterations, then stop gracefully
([ADR-0004](docs/adr/0004-raw-tool-loop.md): a raw loop, not an agent framework). The whole
Knowledge Base lives in the cached system prompt rather than a vector index — it is nine
markdown topics, 62 KB Sections, about 7.2K tokens, so retrieval would only add a way to miss
([ADR-0001](docs/adr/0001-kb-in-prompt-no-rag.md)). Everything third-party sits behind four
**seams** with one production implementation and one test double each — `ModelProvider`
(OpenRouter / stub), `ConversationStore` (Firestore / in-memory), `KnowledgeSource` (markdown
files), `Notifier` (a Firestore write the Console observes) — which is why `make dev` and CI
run the entire Assistant with no API key and no GCP. Firestore is also the event bus: a
thumbs-down write triggers the Triage Agent as a separate Firebase Function, so analysis can
never slow a conversation down ([ADR-0005](docs/adr/0005-event-driven-triage-agent.md)).
Langfuse gets one Trace per Turn with the cost OpenRouter reports.

Read next, in this order:

| Document | What it is |
| --- | --- |
| [`plan.md`](plan.md) | Phases, what shipped, **what was cut and why**, risks — the entry point for the review |
| [`CONTEXT.md`](CONTEXT.md) | The glossary code, tests and docs share (Assistant, Visitor, Turn, KB Section, Escalation, Hand-over…) |
| [`.scratch/cadre-support-agent/spec.md`](.scratch/cadre-support-agent/spec.md) | The super spec: 50 user stories, implementation decisions, testing seams |
| [`docs/architecture.md`](docs/architecture.md) | Diagrams, the data model, the tech-stack table, the capacity model and scaling trade-offs |
| [`docs/adr/`](docs/adr/) | Ten decision records, each with the options that lost |
| [`docs/demo-script.md`](docs/demo-script.md) | The live walkthrough, step by step, with the exact prompts |
| [`docs/transcripts/`](docs/transcripts/) | Deployed-app checks: real Turns, real costs, real Trace ids |
| [`docs/research/`](docs/research/) | The evidence the decisions were made from |
| [`docs/process/`](docs/process/) | The subagent-driven-development ledger: every ruling, every review round |
| [`CLAUDE.md`](CLAUDE.md) | How Claude Code works in this repo — commands, conventions, process rules |

## Run it locally

Python is managed with [uv](https://docs.astral.sh/uv/) (3.12, pinned in `.python-version`);
the web app with `pnpm` (Node 24). Everything goes through the root `Makefile`.

```bash
make install   # uv sync + pnpm install
make dev       # API on http://127.0.0.1:8080 with reload, Vite on http://localhost:5173
```

Open <http://localhost:5173>. **No keys and no GCP account are needed**: the defaults are
`MODEL_PROVIDER=stub` and `CONVERSATION_STORE=memory`, so a scripted stub provider answers a
handful of demo prompts (ask "What does Cadre AI do?", "What does it cost?", "Where do I see
my agents' results?") and Sessions live in process memory. Vite proxies `/api` and `/healthz`
to the API.

To run against the real model, copy [`.env.example`](.env.example) to `.env` — it is the
schema for every environment variable, one line of explanation each — set `OPENROUTER_API_KEY`
and `MODEL_PROVIDER=openrouter`, and optionally `CONVERSATION_STORE=firestore` with
`gcloud auth application-default login`. Nothing in the app reads a dotenv file: `make dev`
passes `--env-file` to uv, and the container gets real environment variables.

## Test it

```bash
make check      # ruff check, ruff format --check, mypy, pytest, eslint, tsc, vitest — what CI runs
make test       # pytest + vitest only
make eval-stub  # the 30 deterministic Eval Cases against the stub provider — free, no key
make eval       # all 50 Eval Cases against the real provider + a Haiku judge (needs OPENROUTER_API_KEY)
```

One test: `uv run pytest api/tests/test_chat.py -k streams`, or
`cd web && pnpm vitest run src/chat/reducer.test.ts`.

Tests exist only at the five seams the spec agreed — S1 HTTP through the API with the stub
provider and in-memory store, S2 pure core units, S3 the Triage Agent handler, S4 the chat
reducer, S5 the eval suite — and never touch OpenRouter, Firestore, Langfuse, Daily or
Firebase Auth. CI ([`.github/workflows`](.github/workflows/)) runs `make check` then
`make eval-stub` on every pull request, with no secrets.

The eval suite ([ADR-0008](docs/adr/0008-pytest-evals-over-ragas.md)) is 50 Eval Cases — 20
in-KB questions with golden answers and expected section ids, 20 Trap Questions with the
strings that would be an invented fact, 10 qualification exchanges — scored on four metrics.
The last full run (Sonnet 5 answering, Haiku 4.5 judging, $0.60):

| Metric | Result |
| --- | --- |
| `correctness` | 19 / 20 |
| `groundedness` | 44 / 50 |
| `escalation_correctness` | 20 / 20 |
| `tool_correctness` | 6 / 10 |

That run is from ticket 13, **before** ticket 11 fixed the two causes of the `tool_correctness`
misses (a job title landing in the `role` Contact Detail instead of counting as the
`company_size_or_role` signal, and signals learned in an earlier Turn being dropped from a
later `capture_lead`). The suite has not been re-run against the real provider since, so treat
6/10 as a floor rather than the current number — see [the honest limits](#honest-limits).

## Deploy it

```bash
make deploy            # gcloud run deploy --source . → cadre-support-agent in us-central1, then curl /api/healthz
make deploy-rules      # firestore.rules + indexes to the Firebase project
make deploy-functions  # rsync core/ and knowledge/ into functions/ and deploy the Triage Agent
```

`make deploy` runs `deploy-secrets` first: it creates the cookie-signing key if it is missing,
copies the three secrets the Firebase Function needs under function-shaped ids, and re-grants
the runtime service account read access to every one — all idempotent, and no secret value is
ever echoed or passed on a command line. Run `make rules` and commit the result whenever
`ADMIN_ALLOWED_EMAILS` changes, so the committed Firestore rules always say what the deployment
says. `make deploy` and `make deploy-functions` share `deploy-secrets`, so **do not run them in
parallel**.

Health checks: `/healthz` exists and is tested, but Google's frontend answers that exact path
on `*.run.app` before the request reaches the container, so probe the deployed service at
`/api/healthz` (the same handler).

## Layout

| Path | What lives there |
| --- | --- |
| `api/` | FastAPI: the composition root (`main.py`), chat, console, handover, feedback, leads routes, session cookie |
| `core/` | The seams and their pure logic: turn loop, prompt, knowledge compiler, redaction, qualification, handover state machine, tools, tracing, SSE, config, logging |
| `core/adapters/` | One implementation per seam — third-party SDKs are imported only here |
| `knowledge/` | The Knowledge Base: nine markdown topics, every heading a citable KB Section |
| `web/` | React + Vite + Tailwind — `src/chat/` (the widget), `src/site/` (mock host page), `src/portal/` (demo Portal), `src/console/` (Strategist Console) |
| `evals/` | The 50 Eval Cases, four metrics, the judge, the runner and its scorecard |
| `functions/` | The Triage Agent as a Firebase Function (gen2, Python) — a thin wrapper over `core/triage.py` |
| `scripts/` | The credentials wizard, the Firestore-rules renderer, the ticket→tasks generator |
| `.scratch/cadre-support-agent/` | The spec and the 20 tickets, each with its status and PR |

## Honest limits

Things a reviewer would otherwise have to discover. None of these block the demo; all of them
are deliberate, and the reasoning is in `plan.md`'s cut log or the linked ADR.

- **One demo Strategist account.** The allowlist holds the operator's Google address and
  `strategist@cadre-demo.example`. Availability is a single toggle, so two people signed in as
  the demo account share one presence document.
- **Sessions never expire.** There is no Firestore TTL policy on `sessions`; a Session ends
  politely after `MAX_TURNS_PER_SESSION` (40) Turns, but the documents stay. Parked from
  ticket 03 as a Phase-2 item.
- **The eval scorecard predates ticket 11's fixes** (see the table above); `make eval` costs
  about $0.60 and a few minutes to refresh it.
- **The Langfuse dataset-run upload is a no-op.** `evals/sink.py` is a seam with nothing behind
  it: langfuse 4.15 removed `dataset_item.link`, and wiring the replacement was cut rather than
  guessed at. Traces, scores and Triage comments *are* live; only the dataset run is missing.
- **Thumbs need a Trace id.** Feedback is keyed by the Langfuse trace id, so with no Langfuse
  keys configured the thumbs do not appear. Decoupling Feedback from Langfuse is Phase 2.
- **Secret copies do not auto-rotate.** The Firebase Function cannot name a hyphenated Secret
  Manager id, so `deploy-secrets` keeps `OPENROUTER_API_KEY` / `LANGFUSE_PUBLIC_KEY` /
  `LANGFUSE_SECRET_KEY` as *copies* of the hyphenated originals. Rotating one does not update
  the other — add a version to both.
- **One flaky test.** `core/tests/test_redaction.py`'s `spoken-dots` case asserts a wall-clock
  bound on the redactor (it guards a real request-path DoS that took 54 s before it was fixed
  and takes 2.7 ms now). Under a loaded CI runner it can exceed its margin; re-run it.
- **A Visitor who leaves a video call locally leaves the Handover Request open** — the
  Strategist's "End call" is what closes it. A `pending_strategist` request that nobody claims
  times out lazily, on the widget's own status poll, so a Visitor who closes the tab leaves the
  request pending until someone looks.
- **Names and street addresses stay in Traces.** The `full` Redaction Profile tokenises emails
  and phones and the `refuse` profile keeps cards, government ids and credentials out of the
  model and the store entirely — but model-driven redaction of names is an explicit Phase-2
  deferral ([ADR-0006](docs/adr/0006-two-profile-pii.md)).
- **Single region, single provider, no fallback.** Firestore `nam5`, Cloud Run `us-central1`,
  OpenRouter with no cross-provider failover. The binding capacity constraint is the provider's
  rate-limit tier, not this app — the numbers are in
  [architecture §8](docs/architecture.md#8-capacity-model).
- **Three optional tickets were not built** (model benchmark, capacity smoke test, in-app
  navigation), so the default model is a reasoned choice rather than a measured one and the
  capacity table is a model rather than a measurement. Both are recorded in `plan.md`'s cut log.
- **The two-device video recording and the signed-in Console screenshots are the operator's**,
  not automated: they need a second screen with a Strategist signed in. Everything reachable
  without a browser session is recorded in [`docs/transcripts/`](docs/transcripts/); the
  signed-out Console checks (401s, Firestore rules denials) are there too.
