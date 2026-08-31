---
status: accepted
date: 2026-08-30
---

# BANT-lite qualification computed in code from tool arguments

Lead qualification is a 0–5 qualification score computed in code from the arguments the model passes to `capture_lead`: industry fit, company size or role, a concrete initiative or pain, timeline or budget, and explicit intent to talk to someone. A score of 3 or more unlocks the live hand-over offer (ADR-0007), made once per session. The model extracts signals; it never assigns the score.

## Context

- "How do I book a call" has no self-serve answer on cadreai.com: there is no calendar, every CTA goes to the /contact form, and the alternatives are hello@gocadre.ai and (619) 324-3223. The bot's lead capture is therefore the booking path, and the console is where a Strategist picks it up.
- A live hand-over consumes a Strategist's time in real time. Offering it to every visitor who says "can I talk to someone" interrupts strategists for students, vendors and the curious; never offering it defeats the vision. The offer needs a gate a Strategist can read and argue with.
- Cadre's own best-fit statement (homepage FAQ): companies of all sizes but especially "businesses with manual workflows that get less efficient as they grow", B2B and B2C services, and PE-backed companies. Nine industries are listed on /industries (the brief names seven). Industry fit is a checkable signal.
- Budget is a poor first question for a consultancy that publishes no pricing; asking it early is off-brand. Timeline or budget is one signal of five, not a gate.
- A score assigned by the model is unauditable and drifts with the prompt; a score computed in code is a unit test and a binary eval (ADR-0008).

## Decision

- `capture_lead` arguments are the signals, each optional and typed: industry (one of the nine, or other), company size band and role (decision-maker or not), initiative or pain (present or absent), timeline or budget (present or absent), explicit intent (asked to talk to a person or book a call). Contact fields (name, email, phone, company) are captured alongside but do not score.
- Score = number of signals present, 0–5, computed in code and stored on the lead with the raw signals. The model sees the tool description, not the formula.
- Score ≥ 3 and an Strategist online → the model may call `offer_live_handover`, once per session. Score < 3, or nobody online → the bot escalates (contact form, email, phone) and the lead is still captured and visible in the console.
- The tool may be called more than once as signals accumulate; the score is recomputed on each call and the session's single lead is updated, never duplicated.
- The console shows signals, score and the conversation so a Strategist can override by simply joining.

## Considered Options

- Intent-only gating (any "talk to someone" triggers the offer) — lost because it interrupts Strategists for unqualified visitors and gives them nothing to read before joining.
- Offer after N turns — lost because turn count measures patience, not fit.
- Model-assigned score in the tool arguments — lost because it cannot be unit-tested, drifts with the prompt, and turns the eval into a similarity judgement instead of a binary check.
- Full BANT with budget required — lost because the site hides pricing; demanding budget first contradicts the brand and gates almost everyone out.
- HubSpot lead scoring — lost because there is no CRM sync in the MVP; HubSpot is the Phase-2 CRM box (the site already embeds a HubSpot form on /contact).

## Consequences

- Positive: deterministic, explainable to Strategists, testable in the 10 qualification/tool eval cases; the threshold changes in configuration, not in the prompt.
- Positive: the gate composes with Strategist presence and the feature flag (ADR-0007) without touching the model.
- Negative: equal weights are crude; a PE managing partner with no stated timeline scores the same as a student with one.
- Negative: signals are only as good as the model's extraction, and users can say the right words. The console conversation view is the check.
- Negative: sessions are anonymous (ADR-0010), so a returning prospect starts at zero and may produce a duplicate lead across sessions; deduplication by email is Phase 2 alongside CRM sync.
- Reopen when: agents report too many or too few offers (tune weights or threshold), conversion data exists to fit weights, or a lead-enrichment agent (ADR-0005 pattern) adds signals the formula should use.

## Links

- Absence of a booking path, best-fit FAQ, industry list, HubSpot embed: [cadreai-site-facts](../research/cadreai-site-facts.md)
- Related: [ADR-0004](0004-raw-tool-loop.md), [ADR-0005](0005-event-driven-triage-agent.md), [ADR-0007](0007-daily-video-handover.md), [ADR-0008](0008-pytest-evals-over-ragas.md), [ADR-0010](0010-firebase-auth-console.md)
