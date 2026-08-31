---
status: accepted
date: 2026-08-30
---

# Two-profile deterministic PII redaction

PII handling uses a deterministic, validated redactor with two profiles: `refuse` (payment cards, IBANs, government IDs, credentials and one-time codes, sensitive categories) applied before the model sees a message and before it is stored; and `full` (the refuse set plus emails and phone numbers tokenised) applied to traces, logs and notification free text. Typed lead fields stay raw because capturing business contact details is the product. Model-based detection of names and addresses is deferred to Phase 2.

## Context

- Cadre's homepage warns about employees "putting sensitive company information" into LLMs, and /ai-engineering's only security claims are "black-box your data", "stop employees from sharing company secrets on personal LLMs" and "secure, compliant AI tools". A support bot from that company that logs raw card numbers to a third-party tracing service contradicts its owner's pitch on day one.
- Data leaves the process in four directions: OpenRouter (model), Firestore (storage), Langfuse Cloud (traces) and Cloud Logging (logs). Each needs a stated policy.
- This is B2B lead capture: name, work email, phone, company and role are what a prospective client wants to leave and what the console must show a Strategist. Redacting them everywhere breaks the product; confining them to typed lead fields keeps them out of free text.
- A deterministic redactor already exists (the author's PII-redaction skill): regex candidates validated with Luhn (cards), mod-97 (IBAN) and check-digit rules for government IDs, which keeps false positives low, plus guardrail behaviour rules for a customer-facing bot. It runs in microseconds with no model call.
- Model-based redaction costs a call per turn, is non-deterministic, and cannot be guaranteed to run before storage on the failure path.
- Cadre's privacy policy states a 2-year retention and a privacy contact; the site states no DPA, SOC 2 or data-residency commitments (ADR-0001 negative facts), so the bot must never imply them.

## Decision

- Profiles:
  - `refuse`: cards → last four digits, IBANs, government IDs, passwords, API keys and one-time codes, and sensitive-category data. Applied to the user turn before the model call and before the message is written to the session. Guardrail behaviour: acknowledge, do not repeat, say it is not needed and why.
  - `full`: the refuse set plus emails and phones tokenised with a stable placeholder per value within a session. Applied to Langfuse trace input and output, structured logs and the free-text part of handover notifications.
- Typed lead fields (name, email, phone, company, role, industry) are stored raw on the lead and shown in the console; they never appear in trace free text.
- B2B refinements: business contact details are welcome, not refused; company names always survive; confidential business data (revenue, deal names, client lists) is not PII but the bot declines to need it ("a strategist will cover that under NDA") and escalates rather than analysing it.
- Each turn emits a redaction manifest (counts per category, no values) as a Langfuse tag, so the volume of PII attempts is observable without content.
- Phase 2: a model-based second pass for names and addresses; Cloud DLP as the alternative if a client requires a vendor-backed detector.

## Considered Options

- One profile everywhere — lost because either lead capture breaks (full everywhere) or traces leak contact details (refuse everywhere).
- Model-based first pass — lost on cost per turn, non-determinism and the inability to guarantee it runs before storage.
- Google Cloud DLP API in the request path — lost because it adds a paid dependency and latency to every turn of an MVP; it is the Phase-2 second-pass candidate.
- No redaction, rely on Langfuse and Cloud Logging access controls — lost because a pasted card number would sit in three third-party systems before anyone noticed.

## Consequences

- Positive: deterministic, unit-testable, sub-millisecond; traces can be shared with Langfuse Cloud and reviewers without a data-handling conversation; the refusal behaviour is eval-able (ADR-0008 pii and tone traps).
- Positive: the triage agent (ADR-0005) reads already-redacted messages, so it never sees refused data either.
- Negative: regexes miss names, addresses and free-form secrets; Phase 2 exists for that reason.
- Negative: placeholders in traces reduce debuggability of contact-related bugs; the console, not the trace, is where to look.
- Negative: refusing before the model means the model cannot help with a task that legitimately needs the value; no such task exists in this product.
- Reopen when: a client requires DPA-level guarantees, Strategists report false positives on business identifiers, or a Phase-2 feature needs the model to read contact details in free text.

## Links

- Security statements, privacy policy, absent certifications: [cadreai-site-facts](../research/cadreai-site-facts.md)
- Data path and provider data-collection flags: [openrouter-facts](../research/openrouter-facts.md)
- Related: [ADR-0001](0001-kb-in-prompt-no-rag.md), [ADR-0005](0005-event-driven-triage-agent.md), [ADR-0008](0008-pytest-evals-over-ragas.md), [ADR-0010](0010-firebase-auth-console.md)
