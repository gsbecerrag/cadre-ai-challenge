# Framework rubrics

Consistent scales so scores mean the same thing across features. Score quickly — these are 5-minute-per-list rubrics, not analysis projects.

## Riskiest Assumption First (RAT) — for PoCs

Don't score features directly. First list the assumptions the project's success depends on (technical: "the realtime API latency is acceptable"; market: "users will trust an AI on calls"; operational: "we can transcribe Spanish reliably"). Rank assumptions by: **(probability it's wrong) × (damage if wrong)**. Then rank features by how directly they test the top assumptions.

- **Now** = features that test the #1–2 assumptions
- **Next** = features testing secondary assumptions
- **Later** = features that test nothing (pure build-out)

Table columns: `Assumption tested | Risk level (H/M/L) | Why here`

## ICE — Impact × Confidence × Ease

Each 1–10. Score = I × C × E (max 1000).

- **Impact**: how much this moves the project's single success metric. 9–10 = the product is pointless without it; 5–6 = clearly helps; 1–2 = cosmetic.
- **Confidence**: how sure you are about the Impact score. 9–10 = direct evidence; 5–6 = strong reasoning, no data; 1–3 = pure hope. Be stingy — most MVP guesses deserve ≤6.
- **Ease**: 9–10 = hours; 6–8 = a day or two; 3–5 = a week; 1–2 = multi-week or unknown tech.

Buckets: Now ≈ top scores forming a coherent slice; Later = anything with Confidence ≤ 3 AND Ease ≤ 4 (expensive guesses).

## MoSCoW — for deadline-driven MVPs

- **Must**: the release is a failure without it. Test: "would we delay the date for this?" If no, it's not a Must.
- **Should**: painful to omit, but shippable without.
- **Could**: nice, grab if time appears.
- **Won't (this time)**: explicitly out. Always populate this — an empty Won't means the exercise failed.

Guardrail: Musts should be ≤ 60% of estimated effort so Should/Could absorb overruns. If Musts exceed that, force-rank them (the "deadline moved up 50%" question).

Mapping: Must → Now, Should → Next, Could/Won't → Later.

## RICE — Reach × Impact × Confidence ÷ Effort

Only when real usage/user data exists.

- **Reach**: people/events per period affected (real number from data, not a guess).
- **Impact**: 3 = massive, 2 = high, 1 = medium, 0.5 = low, 0.25 = minimal.
- **Confidence**: 100% / 80% / 50%. Below 50% → don't score it, move to Later as "needs evidence".
- **Effort**: person-weeks (or person-days for small teams — pick one unit and keep it).

## WSJF-lite — Cost of Delay ÷ Duration

For dependency-heavy or sequencing problems. Score each 1–10:

- **Cost of Delay** = user/business value + time criticality + risk reduction/unblocking (average the three, or just gut-score 1–10 with unblocking weighted heavily)
- **Duration**: relative size (1 = smallest item on the list, 10 = largest)

Highest CoD/Duration first. Items that unblock other items get their CoD boosted explicitly — note it in the "why" column.

## Value/Effort matrix

Score Value 1–10 (contribution to the project's one success metric) and Effort 1–10 (relative size). Quadrants:

- High value / low effort → **Now** (quick wins)
- High value / high effort → **Now or Next** — split it if possible; a splittable big rock often hides a quick win
- Low value / low effort → **Next/Later** (filler — only when idle)
- Low value / high effort → **Cut** (time-sinks; name them in "Deliberately NOT doing")
