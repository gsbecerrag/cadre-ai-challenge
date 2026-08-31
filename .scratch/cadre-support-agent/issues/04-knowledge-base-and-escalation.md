# 04: Complete Knowledge Base and honest Escalation on Trap Questions

**What to build:** A Visitor can ask anything the brief lists — what Cadre does, which industries, how to book a call, the Portal, the AI Maturity Index, model selection and data security — and get a Grounded Answer with citations; and when they ask a Trap Question (pricing, a Portal login URL, SOC 2 or a DPA, headcount, a named consultant, a competitor comparison, an outcome guarantee) the Assistant gives an honest Escalation: what it knows, what it cannot confirm, and one concrete next step. This slice authors the full Knowledge Base from the research (services, the nine industries, the eight case studies, the AI Maturity Index and the eight pillars, the engagement process and the 45-day intensive, partners and model selection, the published data-security commitments, the Portal, contact details and team, and an explicit "what Cadre does not publish" topic), writes the grounding and escalation rules and the Trap Question list into the system prompt, adds the `escalate` tool (reason, next step), renders citations in the chat as links to the section, and answers in the Visitor's language (English or Spanish). Phase P1.

**Blocked by:** 02 (First Turn end-to-end with the stub provider)

**Design reference:** [docs/design](../../../docs/design/README.md) — brief §2.5 kind 3: the Escalation card (3 px `#db4545` left border, radius `6px 16px 16px 6px`, title, body, boxed "Next step:" line, citations). The pricing and generic-fallback copy in §2.5 is the reference wording, in English and Spanish.

**Status:** done

- [x] Every fact in the Knowledge Base traces to the research files or the brief; the "what Cadre does not publish" topic lists pricing, Portal login, certifications, headcount, and named availability.
- [x] The compiled Knowledge Base stays under the token budget recorded in the architecture doc, and every section id is unique; covered at seam S2.
- [x] A Turn in which the provider calls `escalate` streams an Escalation that names the next step and contains no invented fact; covered at seam S1 with the stub.
- [x] Citations in the answer render as inline references that reveal the section's title on hover or tap.
- [x] A Spanish message receives a Spanish answer (prompt rule; verified manually on the deployed app and recorded in the PR).
- [x] Manual verification on the deployed app of the six brief scenarios plus three Trap Questions (pricing, Portal URL, SOC 2), with the transcripts attached to the PR.
- [x] Escalations render as the design's Escalation card with the "Next step:" line; the pricing and generic-fallback wording follows the design reference.

## Comments

- Delivered in [PR #10](https://github.com/gsbecerrag/cadre-ai-challenge/pull/10). Reviewer: Approved, every KB fact traced to the research or the brief; two Important items (a Spanish test that could not fail; two demo-script citations on the wrong sections) and six honesty edits fixed in round 1; scoped re-review: all addressed, no new breakage.
- Ruling: `escalate(reason enum, next_step, known, language)` with per-reason EN/ES copy from the design; the `escalation` payload stays `{title, body, next_step, citations}`.
- Ruling: Assistant directives live in the prompt rules, never inside citable KB bodies; the KB states facts, including the fact that something is not published.
- Ruling: the "Next step:" label follows the chrome EN/ES toggle for now — an optional `language` field on the escalation payload is carried to ticket 08.
- Ruling: the generic-fallback body is the design sentence trimmed before its embedded "Next step:"; the PE Playbook price lives in `not-published#pricing` (no `events` topic).
- Deferred to the controller after ticket 03 lands the real provider: deployed-app transcripts of the six brief scenarios, three Trap Questions (pricing, Portal URL, SOC 2), and a Spanish exchange — recorded here when done.
- Parked: a positive "worth a conversation" nudge for off-list industries (dropped from the KB with the directive move; add to the prompt rule if evals show refusals); duplicated facts across topics; empty H1 sections (ticket 02 shape); the figure-to-section guard is hand-maintained (the general form belongs to the eval suite, ticket 13).
- Deployed-app check recorded: [docs/transcripts/2026-08-31-deployed-checks.md](../../../docs/transcripts/2026-08-31-deployed-checks.md) — revision `0b118a7` on the public URL with Claude Sonnet 5 through OpenRouter and Firestore Sessions; six scenarios, three Trap Questions, Spanish, and a refresh pair; ~0.6–1.3¢ per cached Turn.
