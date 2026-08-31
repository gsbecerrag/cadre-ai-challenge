# Cadre AI Support Agent

The customer-facing AI assistant for Cadre AI (an AI strategy and implementation consultancy): it answers prospects and clients from a curated knowledge base, qualifies leads, and hands warm leads to a human strategist. This glossary is the vocabulary that code, docs, tickets, and tests must share.

## Language

### Conversation

**Assistant**:
The AI system that talks to visitors on Cadre's behalf.
_Avoid_: bot, chatbot, agent, support agent

**Visitor**:
An anonymous person talking to the Assistant — prospect or existing client alike, until they identify themselves.
_Avoid_: user, customer, client

**Session**:
One Visitor's conversation with the Assistant, identified by a browser cookie and holding the message history.
_Avoid_: chat, thread, conversation

**Turn**:
One Visitor message and the Assistant's complete response to it, including any tool calls it makes on the way.
_Avoid_: exchange, round, request

### Knowledge

**Knowledge Base**:
The curated, versioned set of facts about Cadre the Assistant is allowed to state.
_Avoid_: docs, corpus, RAG, index

**KB Section**:
The smallest citable unit of the Knowledge Base, addressed by a stable id such as `services#ai-strategy`.
_Avoid_: chunk, passage, document

**Grounded Answer**:
An Assistant answer whose every factual claim cites a KB Section.
_Avoid_: verified answer, sourced answer

**Trap Question**:
A Visitor question that sounds answerable but whose answer is not in the Knowledge Base; the correct behaviour is an Escalation, never an invented answer.
_Avoid_: adversarial question, edge case, hallucination test

### Escalation and hand-over

**Escalation**:
The Assistant redirecting a Visitor to a human channel (contact form, callback offer) without a human joining the Session.
_Avoid_: fallback, deflection, hand-off, transfer

**Hand-over**:
A Strategist taking the conversation from the Assistant, either live or by Callback.
_Avoid_: escalation, hand-off, transfer, routing

**Live Hand-over**:
A Hand-over conducted as a video call inside the chat, right now.
_Avoid_: call, meeting, video session

**Callback**:
The Hand-over mode in which a Strategist contacts the Lead later instead of joining now.
_Avoid_: follow-up, ticket

**Handover Request**:
The record of one offered Hand-over and its state, from offered through ended, declined, or no-strategist-available.
_Avoid_: call request, ticket, escalation record

**Strategist**:
A human member of Cadre's team who takes Hand-overs and works in the Console.
_Avoid_: agent, operator, admin, rep

**Availability**:
Whether at least one Strategist is marked online in the Console; it gates whether a Live Hand-over may be offered.
_Avoid_: presence, status

**Console**:
The authenticated web surface where Strategists manage Availability, Handover Requests, and Triage Reports.
_Avoid_: admin panel, dashboard, back office

### Leads

**Lead**:
A Visitor who has shared Contact Details, together with the Qualification Signals collected about them.
_Avoid_: contact, prospect, customer, opportunity

**Contact Details**:
A Lead's name, work email, phone, company, and role — the personal data the product exists to collect, kept in full on the Lead.
_Avoid_: PII (when meaning these), personal data

**Qualification Signal**:
One of the five facts that count toward the Qualification Score: industry fit, company size or role, a concrete initiative or pain, a timeline or budget, and explicit intent to talk or buy.
_Avoid_: BANT field, attribute, criterion

**Qualification Score**:
The 0–5 count of Qualification Signals present on a Lead, computed in code, never by the model.
_Avoid_: lead score, rating, grade

**Qualified Lead**:
A Lead whose Qualification Score meets the configured threshold, which unlocks the offer of a Live Hand-over.
_Avoid_: hot lead, MQL, SQL

### Guidance

**Walkthrough Card**:
A structured Assistant answer to "where do I find X": the steps and the destination, rendered as a card with a link into the Portal.
_Avoid_: tutorial, guide, how-to

**Portal**:
Cadre's client platform for tracking AI tools, agents, training, and results. In this repository it is a demo replica with mock data.
_Avoid_: dashboard, app, platform

### Quality loop

**Feedback**:
A Visitor's thumbs-up or thumbs-down on the Assistant, attached to the Trace of the Turn it judges.
_Avoid_: rating, review, score

**Trace**:
The observability record of one Turn — model, tokens, cost, latency, tool calls — with Contact Details redacted.
_Avoid_: log, span, event

**Triage Agent**:
The independent process, triggered by a thumbs-down, that produces a Triage Report.
_Avoid_: reviewer, judge, analyzer

**Triage Report**:
The Triage Agent's structured analysis of one thumbs-down: category, evidence, and the suggested Knowledge Base addition and Eval Case.
_Avoid_: incident, postmortem, ticket

**Eval Case**:
One scenario in the evaluation suite: a Visitor message, the expected Assistant behaviour, and the metric that judges it.
_Avoid_: test case, scenario, sample

### Personal data

**Refuse Set**:
The personal-data types the Assistant must never hold — payment cards, bank accounts, government IDs, credentials, and sensitive categories — redacted before the model sees them and before anything is stored.
_Avoid_: blocklist, forbidden data, sensitive PII

**Redaction Profile**:
The named set of personal-data types redacted at a boundary: `refuse` (the Refuse Set only) or `full` (the Refuse Set plus Contact Details tokenized).
_Avoid_: mask level, scrub mode
