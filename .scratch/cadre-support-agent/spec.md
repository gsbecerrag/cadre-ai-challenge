# Cadre AI Support Agent — Super Spec

Status: ready-for-agent
Date: 2026-08-30
Vocabulary: [CONTEXT.md](../../CONTEXT.md) · Phases and scope: [plan.md](../../plan.md) · Decisions: [docs/adr](../../docs/adr/) · Diagrams and data model: [docs/architecture.md](../../docs/architecture.md)

This spec is the product requirements document and the engineering source of truth for the MVP. Tickets are derived from it; the Assistant, the Console, the Triage Agent, and the evaluation suite are all specified here.

## Problem Statement

Cadre AI is an AI strategy and implementation consultancy whose inbound team receives a growing volume of inquiries from prospective clients, existing clients, and people who simply want to learn what Cadre does. Today every question ends in the same place: cadreai.com has no booking calendar, no client Portal login, no AI Maturity Index page, and no pricing — every call to action lands on a contact form. Visitors wait for a reply to questions the website could answer, and the team spends its time on conversations that are not yet qualified.

From a Visitor's side: "I want to know whether Cadre works with my industry, what an engagement looks like, how I get my AI Maturity Index score, how I reach the Portal, and how I talk to a real strategist — now, not in two days." Existing clients ask how to access the Portal and what it tracks. Business leaders ask how Cadre picks models and keeps their data safe.

From Cadre's side: "I want the Assistant to answer accurately from what we actually publish, to refuse gracefully when we don't publish it, to tell me which leads are worth a strategist's time right now, and to show me where it fails so we can fix the knowledge, not guess." A support bot that invents a Portal URL or a price is worse than no bot.

This is also a take-home for a Director of AI Engineering role: the system must be deployed on a public URL, evaluated against real scenarios, observable end to end, and built with deliberate, defensible architecture decisions in roughly two days.

## Solution

A customer-facing **Assistant** on a public URL that:

1. Gives **Grounded Answers** from a curated **Knowledge Base** compiled into a prompt-cached system prompt, citing the **KB Section** each claim comes from, and answers in the Visitor's language (English or Spanish).
2. Recognises **Trap Questions** — anything Cadre does not publish — and responds with an honest **Escalation**: what it does know, what it cannot confirm, and the concrete next step (contact form, email, phone, or a Strategist).
3. Turns "how do I…" questions into **Walkthrough Cards** with steps and a destination inside a demo **Portal**, instead of prose that invents URLs.
4. Collects a **Lead** naturally, computes a **Qualification Score** in code from five **Qualification Signals**, and — for a **Qualified Lead** — offers a **Hand-over** once: a **Live Hand-over** on video inside the chat when a **Strategist** is online, a **Callback** otherwise.
5. Gives Strategists a **Console** (Google sign-in, allowlisted) with **Availability**, a realtime list of **Handover Requests** with the Lead's Contact Details and conversation, a Join button for live calls, and a Triage tab.
6. Records every **Turn** as a **Trace** with model, tokens, cost, and latency; collects thumbs-up/down **Feedback**; and, on a thumbs-down, an independent **Triage Agent** writes a **Triage Report** with a category, evidence, a suggested Knowledge Base addition, and a suggested **Eval Case**.
7. Ships with fifty **Eval Cases** (in-KB correctness, Trap Questions, qualification/tool behaviour) scored on four metrics, runnable locally against the real provider and in CI against a stub.
8. Handles personal data with two **Redaction Profiles**: the **Refuse Set** never reaches the model or storage; **Contact Details** are kept on the Lead and tokenised everywhere else.

Deployed as one container on Cloud Run with Firestore, Firebase Auth, a Firebase Function for the Triage Agent, OpenRouter as the sole model provider, Langfuse for observability, and Daily.co for video.

## User Stories

### Visitors — prospective clients

1. As a prospective client, I want to ask what Cadre AI does and get a concise answer with the four core services named, so that I can decide in a minute whether to keep reading.
2. As a prospective client in construction, I want to ask whether Cadre works with my industry and hear which of the nine industries it serves and a relevant case study, so that I feel it applies to me.
3. As a prospective client, I want to ask how an engagement starts and hear about the AI Transformation Intensive and the eight-pillar AI Maturity Index, so that I understand the process before I commit to a call.
4. As a business leader, I want to ask what the AI Maturity Index is and how I get scored, and be told honestly that scoring happens through a strategist conversation that starts with the contact form or a Hand-over, so that I am not sent to a page that does not exist.
5. As a prospective client, I want to ask about pricing and be told plainly that Cadre does not publish pricing, with the one price it does publish if relevant, and an offer to connect me with a strategist, so that I am not misled by an invented number.
6. As a prospective client, I want to ask how Cadre chooses between OpenAI, Anthropic, Google, and other models and get an answer grounded in Cadre's published partner stance and model-tiering approach, so that I can judge their independence.
7. As a prospective client, I want to ask how Cadre keeps my data secure and hear exactly the commitments Cadre publishes — no more — with an Escalation for anything like SOC 2 or a DPA, so that I get a truthful answer.
8. As a prospective client, I want to ask "how do I book a call with an AI strategist" and be offered the fastest real path (a Strategist right now if one is online, otherwise a Callback with my details), so that I do not have to go hunting for a calendar that does not exist.
9. As a prospective client, I want every factual claim the Assistant makes to carry a citation to the KB Section it came from, so that I can trust and verify what I am told.
10. As a prospective client, I want the Assistant to answer in Spanish when I write in Spanish, so that the conversation feels natural.
11. As a prospective client, I want the Assistant to say "I don't have that information" instead of guessing when I ask about headcount, office hours, a specific consultant, or a competitor comparison, so that I keep trusting the answers it does give.
12. As a prospective client, I want to share my name, work email, company, and phone in conversation and have it acknowledged without a lecture, so that giving my details feels normal.
13. As a prospective client who pastes a card number or a government ID by mistake, I want the Assistant to tell me it is not needed and will not be kept, and then continue helping, so that a mistake does not derail the conversation.
14. As a prospective client who shares internal revenue figures, I want the Assistant to say it does not need them and that a strategist covers that under NDA, so that I am not oversharing with a bot.
15. As a Qualified Lead, I want to be asked once — not repeatedly — whether I would like to talk to a strategist right now, so that the offer feels considered rather than pushy.
16. As a Qualified Lead who accepts, I want a video call to open inside the chat within seconds, with the Strategist's name shown, so that I stay in the same window and the lead stays warm.
17. As a Qualified Lead who accepts when no Strategist is online, I want to be told a strategist will call me back and see my details confirmed, so that I know the request was received.
18. As a Visitor, I want to decline a Hand-over and continue chatting, so that I stay in control.
19. As a Visitor, I want to give a thumbs-up or thumbs-down on the conversation and optionally say why, so that Cadre can improve the Assistant.
20. As a Visitor, I want the chat to stream its answer as it is written and to show that it is working during tool calls, so that it feels responsive.
21. As a Visitor, I want a clear, friendly message if something fails behind the scenes, never an error dump, so that the failure does not reflect on Cadre.
22. As a Visitor who tries to make the Assistant ignore its instructions or reveal them, I want it to stay on topic and on brand, so that Cadre's assistant cannot be embarrassed.
23. As a Visitor who asks about something unrelated to Cadre (legal advice, personal matters, general coding help), I want a polite redirect to what the Assistant can help with, so that its scope is clear.
24. As a Visitor returning within the session, I want the Assistant to remember what we discussed, so that I do not repeat myself.
25. As a Visitor on a long conversation, I want a graceful message when the Session's turn limit is reached, with the contact path, so that I am never silently cut off.

### Visitors — existing clients

26. As an existing client, I want to ask how to access the Cadre Portal and be told what it is for, that access is provisioned by my Cadre team, and be offered a Strategist, so that I get the real path rather than a fake login link.
27. As an existing client, I want a Walkthrough Card for "where do I see my agents' results" that shows the steps and opens the matching Portal page, so that I can see where the information lives.
28. As an existing client, I want to ask what the Portal tracks and get the answer Cadre publishes — tools, agents, training, results — so that I know what to expect.

### Strategists

29. As a Strategist, I want to sign in to the Console with my Google account and be refused if my email is not on the allowlist, so that Lead data is never exposed.
30. As a Strategist, I want to toggle my Availability online or offline, so that the Assistant only offers live calls when someone can take them.
31. As a Strategist, I want a new Handover Request to appear in the Console the instant the Assistant creates it, with a sound and a browser notification, so that I never miss a warm lead.
32. As a Strategist, I want each Handover Request to show the Lead's Contact Details, Qualification Signals, score, and the conversation so far, so that I join informed.
33. As a Strategist, I want to claim a request and join the video call from the Console in one click, so that the Visitor is not left waiting.
34. As a Strategist, I want to end the call and see the request marked ended, so that the queue stays accurate.
35. As a Strategist, I want Callback requests listed with the Lead's details, so that I can follow up when I am back.
36. As a Strategist, I want to see Triage Reports for thumbs-down conversations, with the suggested Knowledge Base addition and Eval Case, so that I can fix the knowledge rather than guess at the failure.
37. As a Strategist, I want to open the Trace behind any conversation in Langfuse from the Console, so that I can see exactly what the Assistant did.

### Cadre engineering and operations

38. As a Cadre engineer, I want every Turn traced with model, tokens, cost, latency, tool calls, and the KB Sections cited, so that I can debug a conversation and know what it cost.
39. As a Cadre engineer, I want cost per conversation and escalation rate on a dashboard, so that I can act on thresholds.
40. As a Cadre engineer, I want thumbs-down Feedback to trigger the Triage Agent without any coupling to the chat service, so that analysis can never slow down or break a conversation.
41. As a Cadre engineer, I want Traces and logs redacted of Contact Details and the Refuse Set, so that observability never becomes a data leak.
42. As a Cadre engineer, I want to switch the conversation model with one configuration change and run the same evaluation suite before and after, so that model choices are decisions backed by numbers.
43. As a Cadre engineer, I want to run fifty Eval Cases locally against the real provider and get a scorecard with correctness, escalation, tool, and groundedness metrics, so that I know whether a prompt change helped.
44. As a Cadre engineer, I want pull requests to run lint, unit tests, and the stub-provider subset of the evals with no API spend, so that regressions are caught for free.
45. As a Cadre engineer, I want structured JSON logs with a controllable log level and correlation ids, so that a log line, a Trace, and a Firestore document can be joined.
46. As a Cadre engineer, I want to deploy with one command from my laptop and have the Cloud Run service read secrets from Secret Manager, so that no secret ever lives in an image or a repository.
47. As a Cadre engineer, I want to turn the Live Hand-over off with a flag and have the Assistant degrade to Callbacks, so that a video outage never blocks lead capture.
48. As a Cadre engineer, I want the Knowledge Base to be markdown in the repository with stable section ids, so that a change to what the Assistant may say is a reviewed pull request.
49. As a Cadre engineer, I want to add a Trap Question to the evals in one line, so that every incident becomes a regression test.
50. As a Cadre engineer, I want the app layer proven under a couple of hundred concurrent streams against the stub provider, so that I can state where the real ceiling is (the provider tier) with evidence.

## Implementation Decisions

### Shape and runtime

- One Cloud Run service runs the API (Python, FastAPI) and serves the built single-page web app (React, Vite, TypeScript) from the same origin. The service is stateless: every Turn loads the Session from Firestore and writes back; nothing conversational lives in process memory. (ADR-0003)
- A separate Firebase Function (Python) is the Triage Agent, triggered by Firestore document writes (a create or an update, because a thumbs-up changed to a thumbs-down is an update). It shares the core package with the API by copying it at deploy time. (ADR-0005)
- Firestore Native is the only database and the event bus. Firebase Auth (Google sign-in) protects the Console. Secret Manager holds runtime secrets; the deployed services never read a dotenv file.
- OpenRouter is the only runtime model provider, behind the `ModelProvider` seam. Default conversation model is Claude Sonnet 5 with a one-hour prompt cache on the system prompt; a cheaper model is used as the evaluation judge; the Triage Agent uses the conversation model with structured output. Model ids are configuration. (ADR-0002)
- Four seams, each with one production implementation and one test implementation: `ModelProvider` (OpenRouter, stub), `ConversationStore` (Firestore, in-memory), `KnowledgeSource` (markdown files; Firestore-backed is Phase 2), `Notifier` (Firestore write that the Console observes; Slack/email are Phase 2). Third-party SDKs are imported only inside their adapter.
- The packages are: the API service, the web app, the Triage Agent function, a shared core (seams, redaction, qualification, knowledge compiler, logging, schemas), the evaluation suite, and the Knowledge Base content. Python dependencies are managed with uv; web dependencies with pnpm.

### Knowledge Base and system prompt

- The Knowledge Base is a set of markdown files, one per topic (services, industries, case studies, AI Maturity Index and the eight pillars, engagement process, partners and model selection, data security commitments, Portal, contact and team, what Cadre does not publish). Each heading carries a stable id; the compiler produces KB Sections addressed as `topic#heading`. Content is drawn from the site facts in research and the brief — nothing the Assistant may say exists outside these files. (ADR-0001)
- The system prompt is assembled in a fixed order so the cached prefix is stable: identity and role; the full compiled Knowledge Base with section ids; grounding rules; escalation rules; personal-data guardrails; qualification guidance; response style and language rule; tool usage rules. Volatile content (date, Availability, session facts) comes last, outside the cached block.
- Grounding rule: state only what a KB Section states, cite the section id inline after the claim; if the Knowledge Base does not contain the answer, say so and escalate. Trap Questions are named explicitly in the prompt: pricing, Portal login or URL, SOC 2 / DPA / certifications, headcount and org details, named-employee availability, competitor comparisons, guarantees of outcomes, anything about a client Cadre has not published.
- Escalation rule: an Escalation names what is known, what cannot be confirmed, and one concrete next step: the contact form, the published email or phone, or a Hand-over when the Visitor is a Qualified Lead.
- Language: the Assistant answers in the Visitor's language (English or Spanish); the Knowledge Base is English.

### Conversation API and streaming

- The chat endpoint accepts a Visitor message for a Session and streams Server-Sent Events: text deltas, a tool-call marker while a tool runs, a Walkthrough Card payload, a Hand-over offer, Hand-over state changes, a final event carrying the Trace id and usage, and an error event with a user-safe message. The web app reduces these events into chat state.
- Sessions are anonymous: an opaque server-issued id in an HTTP-only cookie. A Session holds its message history in Firestore (bounded by a configurable turn cap, default forty; reaching it produces a graceful closing message with the contact path).
- The tool loop is a plain loop over the provider: assemble messages (cached block first), call the model with the tool definitions, execute any tool calls, feed results back, repeat up to four iterations, then stop gracefully. Tools: `capture_lead`, `escalate`, `show_walkthrough`, `offer_live_handover`, and (Phase 6 only) `navigate_to`. (ADR-0004)
- Provider adapter behaviours that are decisions, not details: OpenRouter mid-stream errors arrive on a successful HTTP status with an error finish reason and are surfaced as a typed provider error; usage and cost are read from the final usage chunk; the cache-control marker is set on the system block; `temperature` is not relied upon.
- Every request and Turn is logged as structured JSON with severity, session id, request id, and Trace id; log level comes from configuration. Bodies are logged only at debug level and only after the `full` Redaction Profile.

### Leads and qualification

- `capture_lead` takes the Contact Details and the five Qualification Signals as typed arguments; the score is computed in code as the count of signals present (0–5) and stored on the Lead with the signals. The model never assigns a score. Threshold is configuration, default three. (ADR-0009)
- A Lead belongs to a Session; updating details later updates the same Lead. Contact Details are stored raw on the Lead's typed fields.
- The Hand-over offer is made at most once per Session, only for a Qualified Lead, and only through the `offer_live_handover` tool, which is exposed to the model only when the score is at or above the threshold.

### Hand-over

- A Handover Request is created when the Assistant offers a Hand-over. Its state machine: `offered → accepted_by_user → pending_strategist → strategist_joined → in_call → ended`, with exits `declined` (Visitor declines), `no_strategist_available` (no Strategist online, or nobody joins within a timeout → the request becomes a Callback with the Lead already captured), and `callback` mode when the live flag is off. (ADR-0007)
- Mode is decided at acceptance: `video` when the live flag is on and at least one Strategist is online; `callback` otherwise. In video mode the server creates one Daily.co room per request with a short expiry and stores its URL on the request; the chat renders the prebuilt iframe; the Console renders the same room for the Strategist.
- The Notifier's production implementation is the Firestore write itself: the Console subscribes to Handover Requests with a realtime listener and raises a browser notification and a sound on new ones.
- The Visitor accepts or declines through dedicated endpoints; the Strategist claims, joins, and ends through Console endpoints. Every transition is validated server-side against the state machine.

### Console

- The Console is a route group inside the same web app, behind Firebase Auth Google sign-in; the API verifies the ID token on every Console endpoint and checks the email against the configured allowlist. Firestore rules mirror the allowlist for the realtime reads and the presence write. (ADR-0010)
- Pages: Availability (online toggle bound to the Strategist's presence document), Handover queue (pending, in call, callbacks), a request detail with Lead, signals, score, conversation, Join and End, and a Triage tab listing Triage Reports newest first with a link to the Trace.
- A "Demo client" Portal is a set of mock routes in the same web app (dashboard, tools, agents, results/training) with static mock data and a visible "Demo portal · mock data" badge; Walkthrough Cards deep-link into it. It has no auth and no state.

### Feedback and Triage Agent

- Feedback (thumbs up/down, optional comment) is written to Firestore with the Session id and Trace id and mirrored to Langfuse as a score on that Trace.
- The Triage Agent runs on every write of a Feedback document — create or update — and exits immediately unless the rating is, or has just become, thumbs-down; loads the conversation (Refuse-Set-redacted) and Trace metadata, makes one structured-output model call, and writes a Triage Report keyed by the Feedback id (so redelivery is idempotent) with: category (knowledge gap, wrong escalation, hallucination, tone, personal data, bug, other), summary, evidence quotes, suggested Knowledge Base addition, suggested Eval Case, severity, and the model used. It posts the summary back to Langfuse as a comment or score. (ADR-0005)

### Personal data

- The redactor from the adopted skill is the runtime module with two Redaction Profiles. `refuse` (payment cards masked to last four, IBAN, government ids, credentials and one-time codes, sensitive categories) runs on every Visitor message before the model call and before the message is stored. `full` (`refuse` plus emails and phones tokenised with consistent numbered tokens) runs on Trace inputs/outputs, on log bodies, and on free text in notifications. Typed Contact Details on the Lead and the Strategist-facing contact block are never redacted. Redaction counts per Turn are attached to the Trace. (ADR-0006)
- Guardrail behaviour in the prompt: Contact Details are welcomed and captured; the Refuse Set gets "not needed, not kept"; confidential business data is declined politely; nothing from another Session is ever surfaced (the store only reads the current Session).

### Observability

- Langfuse receives one Trace per Turn (nested spans for the model calls and tools), grouped by Session id, with the cost OpenRouter reports, latency, model, tokens, cached tokens, tags for escalated / lead captured / hand-over offered, and the redaction manifest. Feedback scores and Triage summaries attach to the same Trace. Evaluation runs are recorded as dataset runs in the same project.

### Evaluation suite

- Fifty Eval Cases in a JSONL file: about twenty in-KB questions with golden answers and expected section ids; about twenty Trap Questions with the expected behaviour (escalate, no invented facts, correct next step) including three or four prompt-injection variants; about ten qualification cases with the expected tool calls and arguments and the expected score. Metrics: answer correctness (model judge against the golden, paraphrase-tolerant), escalation correctness (binary), tool correctness (expected tool, arguments, score), groundedness (each claim supported by the cited KB Section, judged claim by claim). The judge is a cheaper model behind the same provider seam. Results go to Langfuse as a dataset run and print as a scorecard. The same suite runs across the benchmark models by changing the model id. (ADR-0008)
- Golden answers are drafted from the Knowledge Base and the Trap and qualification cases are hand-validated before they count.

### Configuration and deployment

- All runtime configuration is environment variables documented in the example env file: provider key and model ids, cache TTL, project and region, allowlist, Firebase web config, Langfuse keys and host, Daily key and domain, feature flag, log level, turn cap, qualification threshold, session secret.
- Deployment is a Makefile target that builds the container and deploys to Cloud Run with secrets bound from Secret Manager, plus a target that copies the core package into the function and deploys it. CI on pull requests runs lint, type checks, unit tests, and the stub-provider subset of the evals; nothing in CI calls a paid API.
- Capacity: the API layer's concurrency is Cloud Run instances times per-instance concurrency; the real ceiling is the provider's rate-limit tier. A stub-provider concurrency smoke test (a few hundred virtual users) proves the app layer; no live-API load test is run. Per-Session turn cap is the burst guard.

## Testing Decisions

A good test exercises externally observable behaviour through a seam and would fail if a real behaviour changed: an HTTP request producing the right events, a pure function producing the right value, a handler producing the right document. Tests do not assert on internal calls, prompt wording, or mock interactions; they never touch OpenRouter, Firestore, Langfuse, Daily, or Firebase Auth. Fixtures use obviously fake personal data. Test names use the glossary's vocabulary.

Every implementing subagent works test-first: the failing test is written and run before the production code; the report shows the red run and the green run.

Seams (agreed):

- **S1 — HTTP through the API (primary seam).** FastAPI's test client against the application with the stub provider, the in-memory store, the in-memory notifier, and the auth dependency overridden. The stub provider is scripted per test: given the last Visitor message it returns canned text, a tool call, a usage block, or a mid-stream error. Covers: a chat Turn streams the expected event sequence and cites section ids; a Trap Question yields an Escalation and no invented fact; `capture_lead` produces a Lead with the computed score; a Qualified Lead gets exactly one Hand-over offer; accepting creates a Handover Request in the right mode given Availability and the flag; Strategist endpoints enforce the allowlist and the state machine; Feedback is written and mirrored; Refuse-Set content never reaches the provider or the store; the turn cap produces the closing message; a provider error produces the user-safe error event.
- **S2 — core units.** Pure functions with real edge cases: both Redaction Profiles against the catalog's validated formats; Qualification Score from signals; the Knowledge Base compiler (section ids stable, every heading addressable, total size within budget); OpenRouter response parsing (streamed tool-call assembly, usage and cost, the HTTP-200 mid-stream error); SSE framing.
- **S3 — Triage Agent handler.** The function's handler called with a fake Firestore event and a fake client and the stub provider: thumbs-up is a no-op; thumbs-down writes a Triage Report with the schema; a redelivered event does not write twice.
- **S4 — web.** One Vitest test for the chat reducer: the SSE event sequence produces the expected chat state (streamed text, card, offer, hand-over states, error).
- **S5 — evaluation suite.** A separate pytest marker; the stub-provider subset (escalation and tool cases, deterministic) runs in CI; the full suite runs locally against the real provider on demand.

Prior art: the repository is greenfield; the conventions are FastAPI's test client with dependency overrides for S1, plain pytest for S2 and S3, Vitest for S4. No tests are written for Firestore security rules, Daily or Firebase Auth network calls, Console or Portal page rendering, or deployment scripts; those are verified manually in the honesty pass and recorded there.

## Out of Scope

- Voice, and any channel other than the web chat.
- Vector retrieval, an admin document-upload pipeline, and a Firestore-backed Knowledge Base (Phase 2; reopen when the Knowledge Base exceeds roughly fifty pages or non-engineers must edit it).
- In-page navigation on cadreai.com or the real Portal; the demo Portal is mock data only. The in-app `navigate_to` tool is optional Phase 6.
- Model-driven redaction of names and addresses in Traces (pass 2); Visitor names remain in Traces in the MVP.
- Slack, email, HubSpot, or any CRM integration; runtime MCP servers.
- An agent framework (LangGraph is named for Phase 2), cross-provider fallback, IP-level rate limiting, conversation summarisation.
- Deploy-on-merge, custom domain, multi-region, self-hosted Jitsi, call transcripts.
- Approval workflow for Triage Report suggestions (Phase 2: apply to Knowledge Base and append the Eval Case from the Console).
- A live-API load test.

## Further Notes

- Priority under time pressure is fixed: grounded chat and Escalation, then Callback Hand-over and Console, then evaluations, then Feedback and the Triage Agent, then Live Hand-over. The Triage Agent outranks Live Hand-over if only one fits; the model benchmark, the concurrency smoke test, and in-app navigation are cut first.
- Model choice is a working default (Sonnet 5) until the benchmark produces numbers; the spec does not depend on which model wins.
- Two provider facts remain unconfirmed and are treated conservatively: Sonnet 5's minimum cacheable prefix through OpenRouter (the system prompt is far above any plausible minimum) and paid-key rate limits (the key's remaining credit is read at setup).
- The demo script follows the user stories in order: grounded question with citation → Trap Question → Walkthrough Card into the Portal → Lead capture → Hand-over accepted with the Strategist joining from a second screen → thumbs-down → Triage Report appearing in the Console → the Trace in Langfuse → the evaluation scorecard.
- Every cut made during the build is recorded in the plan's cut log in the same pull request as the change.
