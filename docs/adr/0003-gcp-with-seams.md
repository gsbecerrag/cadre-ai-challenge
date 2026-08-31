---
status: accepted
date: 2026-08-30
---

# Commit to GCP behind four tested seams

The runtime is one Cloud Run container (FastAPI plus the built React SPA), Firestore Native in nam5 as the only database and the event bus, Firebase Auth for the console, and Firebase Functions (Python, gen2) for event-driven agents. We accept GCP lock-in deliberately and confine it behind four seams (`ModelProvider`, `ConversationStore`, `KnowledgeSource`, `Notifier`), each with exactly one production implementation.

## Context

- The gcloud and firebase CLIs were already authenticated on the build machine and Firebase is the author's fastest path; with the repo due 31 Aug, "already logged in" is a real force.
- The chat API streams tokens over SSE and holds a connection for the length of a turn. Cloud Run supports long-lived HTTP streaming, request concurrency (80 per instance by default) and scale-to-zero, which suits a demo that sits idle most of the day.
- the Strategist Console needs realtime updates (a handover request appearing, a triage report landing) without polling. Firestore listeners give that to a browser for free, and Firestore document triggers are how the triage agent is invoked (ADR-0005).
- AWS was the closest alternative and lost on specifics: App Runner's streaming behaviour was unreliable in prior experience and Bedrock's Claude surface has feature gaps (ADR-0002). Vercel lost because its CLI was absent and its Python story is serverless functions, a poor fit for an SSE API that loads history per turn.
- Capacity is bounded by the model provider before the platform: parallel turns ≈ min(instances × 80, provider tokens-per-minute ÷ tokens-per-turn). With a ~25K-token cached prefix per turn, the provider term binds first.

## Decision

- Hosting: one container on Cloud Run serving the API and the static SPA from one origin (no CORS, one deploy, one URL). The API is stateless: session history is loaded from Firestore each turn and no agent state lives in process memory, so any instance can serve any turn.
- Data: Firestore Native (nam5) holds sessions, messages, leads, handover requests, agents, feedback and triage reports. It is also the event bus between the API and background agents.
- Identity: Firebase Auth (ADR-0010). Async work: Firebase Functions Python gen2 on Firestore triggers (ADR-0005). Secrets: Secret Manager. Logs: structured JSON to Cloud Logging carrying session, request and trace IDs.
- Seams, each a small interface with one production implementation:
  - `ModelProvider`: OpenRouter in production; the stub provider in tests, CI and the load smoke test.
  - `ConversationStore`: Firestore in production; in-memory in tests.
  - `KnowledgeSource`: Markdown files in production; tests point it at fixtures. Firestore-backed is Phase 2 (ADR-0001).
  - `Notifier`: a Firestore write the console listens to; tests observe it through the in-memory store.
- Portability rule: a seam counts as portable only if a second implementation is exercised by the test suite. Untested second implementations are slides, not properties, and are not built.
- Deploy is one make target from a laptop; deploy-on-merge is out of scope.

## Considered Options

- AWS (App Runner or Lambda, DynamoDB, Cognito, Bedrock) — lost on streaming reliability, Bedrock feature gaps and no authenticated tooling.
- Vercel with Next.js — lost on absent tooling and no first-class Python server runtime for SSE.
- Fly.io or Railway plus Postgres — lost because auth, realtime listeners and document triggers would each be a separate service to wire in.
- Postgres or Cloud SQL instead of Firestore — lost because it has no client-side realtime listeners or document triggers and never scales to zero.

## Consequences

- Positive: single origin, single deploy, realtime console for free, scale-to-zero cost; the stateless API scales horizontally with no coordination.
- Positive: the seams make the whole loop runnable in CI without keys and allow a 200-virtual-user smoke test against the stub provider.
- Negative: Firestore has no joins and needs composite indexes for compound queries; reporting over leads will eventually want a relational store.
- Negative: nam5 fixes data residency to the US; a client demanding EU residency reopens this.
- Negative: Functions gen2 cold starts add seconds to the first triage report; acceptable on an async path.
- Negative: two deployables (container and functions) share core code by copying at deploy time, which can drift.
- Reopen when: a client requires non-US residency, relational reporting over leads becomes a requirement, or Cadre standardises on another cloud.

## Links

- Bedrock and Vertex feature gaps: [claude-api-facts](../research/claude-api-facts.md)
- Provider limits that bound capacity: [openrouter-facts](../research/openrouter-facts.md)
- Related: [ADR-0001](0001-kb-in-prompt-no-rag.md), [ADR-0002](0002-openrouter-sole-provider.md), [ADR-0005](0005-event-driven-triage-agent.md), [ADR-0010](0010-firebase-auth-console.md)
