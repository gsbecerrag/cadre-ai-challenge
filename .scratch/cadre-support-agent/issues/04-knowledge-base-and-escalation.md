# 04: Complete Knowledge Base and honest Escalation on Trap Questions

**What to build:** A Visitor can ask anything the brief lists — what Cadre does, which industries, how to book a call, the Portal, the AI Maturity Index, model selection and data security — and get a Grounded Answer with citations; and when they ask a Trap Question (pricing, a Portal login URL, SOC 2 or a DPA, headcount, a named consultant, a competitor comparison, an outcome guarantee) the Assistant gives an honest Escalation: what it knows, what it cannot confirm, and one concrete next step. This slice authors the full Knowledge Base from the research (services, the nine industries, the eight case studies, the AI Maturity Index and the eight pillars, the engagement process and the 45-day intensive, partners and model selection, the published data-security commitments, the Portal, contact details and team, and an explicit "what Cadre does not publish" topic), writes the grounding and escalation rules and the Trap Question list into the system prompt, adds the `escalate` tool (reason, next step), renders citations in the chat as links to the section, and answers in the Visitor's language (English or Spanish). Phase P1.

**Blocked by:** 02 (First Turn end-to-end with the stub provider)

**Status:** ready-for-agent

- [ ] Every fact in the Knowledge Base traces to the research files or the brief; the "what Cadre does not publish" topic lists pricing, Portal login, certifications, headcount, and named availability.
- [ ] The compiled Knowledge Base stays under the token budget recorded in the architecture doc, and every section id is unique; covered at seam S2.
- [ ] A Turn in which the provider calls `escalate` streams an Escalation that names the next step and contains no invented fact; covered at seam S1 with the stub.
- [ ] Citations in the answer render as inline references that reveal the section's title on hover or tap.
- [ ] A Spanish message receives a Spanish answer (prompt rule; verified manually on the deployed app and recorded in the PR).
- [ ] Manual verification on the deployed app of the six brief scenarios plus three Trap Questions (pricing, Portal URL, SOC 2), with the transcripts attached to the PR.
