---
name: mvp-prioritization
description: Prioritize features for an MVP, PoC, pilot, or early-stage product by selecting the best-fit prioritization framework (RICE, ICE, MoSCoW, Value/Effort, WSJF-lite, Riskiest Assumption First) for the situation and applying it to produce a Now/Next/Later table with a clear MVP cut line. Use this skill whenever the user shares a PRD, spec, feature list, or scope document and wants to prioritize, scope, cut, sequence, or decide "what to build first" — even if they don't name a framework or say "prioritize" explicitly (e.g., "this is too big, help me trim it", "what should v1 include?", "which of these features matter for the demo?").
---

# MVP Prioritization

Turn a PRD or spec into a defensible, prioritized plan. The core insight: no single framework is "best" — the best framework depends on what the project is trying to learn or prove, how much data exists, and what constraints dominate. Your job is to diagnose the situation, pick the framework that fits, apply it honestly, and deliver a Now/Next/Later table with a clear MVP cut line.

## Workflow

### Step 1 — Extract the feature set

Read the PRD/spec and pull out a flat list of candidate features/capabilities. Normalize granularity: split anything that's really 2+ separable deliverables; merge fragments that can't ship independently. Aim for items sized so each could plausibly be one row in the table (roughly "a thing a developer could scope"). If the document buries features in prose, extract them faithfully — don't invent features that aren't implied by the doc.

### Step 2 — Diagnose the situation

Determine these from the document (and ask the user ONLY for what you genuinely cannot infer — one short round of questions max):

- **Project type**: PoC (proving something works) vs MVP (first usable product) vs pilot/demo (impressing a specific audience by a date)
- **Dominant risk**: technical feasibility, user desirability, viability/cost, or delivery deadline
- **Evidence available**: real usage data / user research vs founder intuition only
- **Hard constraints**: fixed deadline, fixed budget, dependency chains, external blockers
- **Team size**: solo/tiny team vs multiple parallel workstreams

State your diagnosis in one short paragraph before prioritizing. This forces honesty and lets the user correct you cheaply.

### Step 3 — Select the framework

| Situation | Framework | Why it wins here |
|---|---|---|
| PoC — the point is to prove/disprove something | **Riskiest Assumption First (RAT)** | A PoC that builds safe features first proves nothing. Rank by how much each item de-risks the core bet. |
| MVP with a hard deadline or demo date | **MoSCoW** | Deadlines need a negotiated cut line, not scores. Must/Should/Could maps directly to what ships. |
| MVP, no usage data, moving fast | **ICE** (Impact × Confidence × Ease) | Fast, low-ceremony scoring that admits uncertainty via the Confidence term. |
| Larger backlog WITH real usage/user data | **RICE** (Reach × Impact × Confidence ÷ Effort) | Reach is only meaningful with data. Don't use RICE when Reach would be pure guesswork. |
| Heavy dependencies / sequencing matters most | **WSJF-lite** (Cost of Delay ÷ Duration) | When order matters more than inclusion, sequence by what's expensive to delay and cheap to do. |
| Small scope (< ~12 items), solo builder, ambiguity everywhere | **Value/Effort matrix** | The simplest tool that works. Quick wins surface immediately; time-sinks are exposed. |

Pick ONE primary framework. Hybrids are allowed only as tie-breakers (see below), never as the headline method — mixing frameworks mid-scoring destroys comparability. If two frameworks genuinely fit, pick the simpler one and say why.

Read `references/frameworks.md` for the scoring rubrics before applying any framework — it defines the scales so scores are consistent rather than vibes.

### Step 4 — Apply it

Score/classify every feature using the rubric. Show your work compactly (scores in the table, not paragraphs per feature). Then apply universal tie-breakers, in order:

1. **Unblockers first** — anything that gates other items or other people ranks up
2. **Quick wins first** — among similar value, cheaper ships earlier
3. **Learning value** — for PoCs/MVPs, items that generate evidence beat items that only add polish

### Step 5 — Deliver the output

ALWAYS use this exact structure:

```markdown
# Prioritization: [Project name]

**Framework: [name]** — [1–2 sentences: why this framework fits this situation]

**Diagnosis**: [project type, dominant risk, key constraints — the Step 2 paragraph]

## Now (the MVP cut)
| # | Feature | [Framework columns, e.g. Impact/Confidence/Ease/Score] | Why here |
|---|---------|---|---|

## Next
| # | Feature | [scores] | Why here |

## Later (or Cut)
| # | Feature | [scores] | Why here |

## The cut line
[2–3 sentences: what "Now" delivers as a coherent whole — a usable walking skeleton or a
conclusive proof, not a pile of parts. If removing one more item would break coherence, say so.]

## Riskiest assumptions still open
- [assumption] → [cheapest way to test it]

## Deliberately NOT doing
- [feature] — [one-line reason: premature, low evidence, post-validation, etc.]
```

Rules for the output:
- **"Now" must be coherent**, not just top-scoring items. An MVP is the smallest thing that works end-to-end; a PoC is the smallest thing that's conclusive. If the top scorers don't form that, promote the missing connective piece and say you did.
- **"Now" should be small.** If more than ~40% of features land in "Now", the cut line isn't doing its job — push harder.
- **Every row gets a "why"** — one short phrase, not a paragraph. The table should be scannable.
- **"Deliberately NOT doing" is mandatory.** Explicitly naming cuts is what makes prioritization real; a list where nothing dies is a roadmap, not a priority call.
- Deliver in chat as markdown by default. Offer an HTML file version only if the user wants a shareable/revisitable artifact or asks for one.

## Edge cases

- **No PRD, just a brain dump**: still works — do Step 1 extraction from the dump, flag that granularity is rough.
- **User insists on a specific framework**: use it, but if it's a poor fit (e.g., RICE with zero data), note the mismatch in one sentence and compensate (e.g., widen Confidence penalties).
- **Everything looks like a "Must"**: this is the most common failure. Force ranking within Musts by asking "if the deadline moved up 50%, what survives?" — the answer is the real Now.
- **PRD describes multiple products/phases**: prioritize within the earliest phase only; list later phases under "Later" wholesale.
