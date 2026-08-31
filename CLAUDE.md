# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

A take-home challenge for Cadre AI: build a **customer support chatbot for Cadre AI** (an AI strategy and implementation consultancy), deploy it to a public URL, and walk through it in a live review. The full brief is in [Cadre_AI_Chatbot_Take_Home_Candidate.docx.md](./Cadre_AI_Chatbot_Take_Home_Candidate.docx.md) — read it before making scope or architecture decisions.

**Start with [plan.md](./plan.md)** — phases, scope decisions, status, and the document map. Then [CONTEXT.md](./CONTEXT.md) for the vocabulary every name and test must use, the super spec at `.scratch/cadre-support-agent/spec.md`, and [docs/architecture.md](./docs/architecture.md). Decisions with reasoning live in `docs/adr/`; evidence in `docs/research/`.

The scaffold is in place (ticket 01). Keep "Commands & Architecture" below current as each slice lands.

## Hard Deliverables

These are non-negotiable requirements from the brief:

- A deployed, publicly accessible URL of the chatbot
- Code pushed to a GitHub repository
- `CLAUDE.md` at the project root (this file)
- `plan.md` at the project root — must break the project into phases and make scope decisions explicit (what's in, what's deliberately out, and why)

## What the Chatbot Must Handle

Minimum bar: a prospective or existing Cadre AI client can plausibly use it to get answers. Starting scenarios from the brief:

- What Cadre AI does and which industries it serves (B2B: professional services, PE, financial services, real estate, construction, manufacturing, retail)
- How to book a call with an AI strategist
- How to access the Cadre portal (tracks AI tools, agents, results)
- What the AI Maturity Index is and how to get scored
- Cadre's approach to LLM selection and data security
- Questions the bot can't answer — it must escalate or redirect, not hallucinate

Cadre facts for the knowledge base: core services are AI Strategy, AI Leadership & Facilitation, AI Engineering, and AI Agents. Key partners: OpenAI, Anthropic (Claude), Google, Microsoft, AWS, Salesforce, Snowflake, OpenRouter. Website: cadreai.com.

## Working Conventions (from the brief — the evaluators are watching these)

- **Plan before coding.** plan.md drives the work; keep it current as scope shifts.
- **Deploy early.** Get a hello-world live on the public URL before building features; iterate against the deployed app.
- **Small, frequent commits** with descriptive messages — never one giant commit at the end.
- **Cut scope aggressively.** 3 working features beat 8 broken ones. Record every cut in plan.md.
- **Verify all generated code.** Test as you go; when debugging, feed real error output back rather than re-running the same prompt.
- **Use subagents for independent tasks** (e.g. parallel research, isolated feature builds) rather than one massive prompt.

Evaluation weights, for prioritizing effort: Claude Code proficiency 30%, system design & architecture 25%, speed & scope 20%, code quality 15%, communication 10%. Architecture discussion in the review focuses on system prompt design, API structure, data model, and scaling trade-offs — make those decisions deliberately and be ready to defend them.

## Git Workflow

`main` is the deployed branch and only moves by pull request. Every change, however small, goes on a short-lived branch and lands via a PR:

- **Branch** from up-to-date `main`, named `<type>/<short-slug>` — `feat/chat-api`, `fix/escalation-loop`, `chore/deploy-config`, `docs/plan-phase-2`.
- **Commit** in [Conventional Commits](https://www.conventionalcommits.org) form (`type(scope?): imperative summary`), one logical change per commit; the body says *why*.
- **Open the PR** with `gh pr create --base main`; the body names the plan.md phase or `.scratch/` ticket it delivers.
- **Merge** with `gh pr merge --merge --delete-branch` — a merge commit keeps the granular commits and the branch shape visible in history.

## Build Process

Work is tracked as tickets: the spec is `.scratch/cadre-support-agent/spec.md`, tickets are `.scratch/cadre-support-agent/issues/NN-slug.md`, and `.scratch/cadre-support-agent/tasks.md` is the generated index that subagent tooling reads. Work the frontier: any ticket whose `Blocked by` tickets are all done.

- **One ticket = one branch = one PR.** Claim it by setting its `**Status:**` to `in-progress`; on merge set `done` with the PR link under `## Comments`, and tick the matching box in `plan.md` in the same PR.
- **Execute tickets with `superpowers:subagent-driven-development`**, `PLAN_FILE=.scratch/cadre-support-agent/tasks.md`: a fresh implementer subagent per ticket, an independent reviewer after it, rulings ledgered and the ledger copied to `docs/process/`. File-disjoint tickets may run in parallel worktrees.
- **TDD is required for every implementing subagent**: `superpowers:test-driven-development` is the loop (show the failing test before the code), `mattpocock-skills:tdd` sets test quality and seams. Tests exist only at the seams named in the spec's Testing Decisions; the subagent's report shows RED then GREEN output.
- **Unit tests and CI use the stub provider and the in-memory store** — OpenRouter, Firestore, Langfuse, Daily, and Firebase Auth are reached only from `make eval` and the deployed app.
- **Personal data:** follow the `pii-redaction` skill (`.claude/skills/pii-redaction/`) — Contact Details are captured, the Refuse Set is never held; tests and fixtures use obviously fake values.
- **Downgrade rule:** a ticket that exceeds 2× its estimate or reaches fix-round 3 is finished directly by the controller (still TDD, one `mattpocock-skills:code-review`) and the ruling is logged in `plan.md`.

## Commands & Architecture

Python is managed with `uv` (3.12, pinned in `.python-version`), the web app with `pnpm` (Node 24). Everything runs through the root `Makefile`:

```
make install    # uv sync + pnpm install
make dev        # API with reload on :8080 and Vite on :5173 (Vite proxies /api and /healthz)
make check      # ruff check, ruff format --check, mypy, pytest, eslint, tsc, vitest — what CI runs
make test       # pytest + vitest only
make build-web  # build web/dist so the API can serve it
make deploy     # gcloud run deploy --source . to cadre-support-agent in us-central1, then curl the health endpoint
```

One test: `uv run pytest api/tests/test_healthz.py::test_healthz_names_the_service_and_version`, or `cd web && pnpm vitest run src/App.test.tsx`.

Layout: `api/` (FastAPI), `web/` (React + Vite + Tailwind), `core/` (shared config, logging, and later the seams and redaction), `knowledge/`, `evals/`, `functions/` (Triage Agent). One root `pyproject.toml` covers `api` and `core` — one lockfile, one venv, one install step in the container.

Architecture: **one Cloud Run container** serves the API and the built SPA from the same origin (ADR-0003), so there is no CORS and one deploy. `api/main.py` is the composition root: it loads settings, configures logging, adds the request-id middleware, registers routes, then mounts `web/dist` at `/` with a single-page fallback — routes are registered before the mount, so the API always wins. Configuration is typed in `core/config.py`, read from environment variables with `.env.example` as the schema; nothing reads a dotenv (the container gets real variables, `make dev` passes `--env-file` to uv). Logging is `core/logging.py`: one JSON object per line with `severity`, `message`, `timestamp`, `request_id` and `session_id` when known — `print` is a lint error.

Note on health checks: `/healthz` exists and is tested, but Google's frontend answers that exact path on `*.run.app` before the request reaches the container, so the deployed service is probed at `/api/healthz` (the same handler).

## Agent skills

### Issue tracker

Local markdown: specs and tickets live as files under `.scratch/<feature-slug>/` in this repo (no GitHub Issues). See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`), recorded as a `Status:` line in each issue file. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` plus `docs/adr/` at the repo root, created lazily by `/domain-modeling`. See `docs/agents/domain.md`.
