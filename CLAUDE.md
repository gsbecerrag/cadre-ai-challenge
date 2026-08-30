# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

A take-home challenge for Cadre AI: build a **customer support chatbot for Cadre AI** (an AI strategy and implementation consultancy), deploy it to a public URL, and walk through it in a live review. The full brief is in [Cadre_AI_Chatbot_Take_Home_Candidate.docx.md](./Cadre_AI_Chatbot_Take_Home_Candidate.docx.md) — read it before making scope or architecture decisions.

There is **no application code yet**. When the stack is chosen and scaffolded, update this file with the actual build/run/test commands and architecture (see the placeholder section at the bottom).

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

## Commands & Architecture

*Not yet applicable — no code exists. Once scaffolded, replace this section with: how to install deps, run the dev server, run tests (including a single test), lint, and deploy; plus the big-picture architecture (where the system prompt lives, how the chat API flows, what the data model is, how escalation works).*

## Agent skills

### Issue tracker

Local markdown: specs and tickets live as files under `.scratch/<feature-slug>/` in this repo (no GitHub Issues). See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`), recorded as a `Status:` line in each issue file. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` plus `docs/adr/` at the repo root, created lazily by `/domain-modeling`. See `docs/agents/domain.md`.
