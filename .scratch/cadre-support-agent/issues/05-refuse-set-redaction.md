# 05: The Refuse Set never reaches the model or storage

**What to build:** A Visitor who pastes a payment card, a government id, a password, or a one-time code is told plainly that it is not needed and will not be kept, and the conversation continues — while the raw value never reaches the model, Firestore, or a log line. This slice lifts the adopted redaction skill's deterministic redactor into the core package as the runtime module with the two Redaction Profiles: `refuse` (cards masked to last four, IBAN masked, government ids and credentials replaced by typed tags, sensitive categories tagged) applied to every Visitor message before the provider call and before the message is stored; `full` (`refuse` plus emails and phones tokenised with consistent numbered tokens) applied to log bodies and, later, to Traces and notifications. Contact Details are not touched by `refuse`. The system prompt gains the guardrail rules from the skill's B2B adaptation (Contact Details welcomed, Refuse Set declined without echoing, confidential business data politely declined). Per-Turn redaction counts are recorded on the Turn for later tagging. Phase P1.

**Blocked by:** 02 (First Turn end-to-end with the stub provider)

**Status:** done

- [x] The `refuse` profile masks a Luhn-valid card to its last four, tags a valid SSN and a valid cédula, tags a labelled password, and leaves an order-like number, an email, and a phone untouched; the `full` profile additionally tokenises emails and phones consistently within one text; covered at seam S2 with fixtures from the skill's catalog (fake values only).
- [x] A Visitor message containing a card number reaches the stub provider already masked and is stored masked; covered at seam S1 by inspecting what the stub received and what the in-memory store holds.
- [x] Debug-level log bodies pass through the `full` profile; covered at S2 with a captured log record.
- [x] The Turn's redaction counts are available on the Turn result (for the Trace tag in a later ticket); covered at S1.
- [x] Manual check on the deployed app: pasting a fake card number yields the "not needed, not kept" reply and the Firestore message shows the masked form; recorded in the PR.

## Comments

- Delivered in [PR #15](https://github.com/gsbecerrag/cadre-ai-challenge/pull/15). Reviewer: two Important false-positive classes (credential labels swallowing the next word; bare 10-digit cédula detection eating unformatted phones) and four minors fixed in round 1; scoped re-review: all addressed, no new breakage.
- Ruling: `refuse` never damages a Contact Detail (ADR-0006) — bare 10-digit cédula detection is label-gated (`cédula`/`CC`/`C.C.`/`documento`/`id`); an unlabelled cédula paste reaches the model, which is the cheaper miss. Credential labels fire only with an explicit separator or a digit in the value.
- Ruling: the hook returns `Redaction(text, counts)` at ticket 02's single call site; counts ride on the `done` event as an optional `redactions` map; log bodies go through `full` inside the JSON formatter with a fixed `[unredactable]` fallback.
- Ruling: the skill catalog's two illustrative values that fail their own validators were replaced by check-digit-valid fakes in fixtures; five behavioural departures from the skill's script are false-positive fixes.
- Parked: the O(n²) obfuscated-email alternative in `full` (ticket 06 must bound it before tracing bodies through `full`); invalid-range SSNs counted as `gov_id`; names/addresses still stored (ADR-0006 Phase 2); a logging-state fixture duplicated across two test files until a ticket owns `conftest.py`.
- Deployed-app check (a fake card yields the "not needed, not kept" reply and Firestore holds the masked form) is recorded by the controller after the merge.
- Deployed-app check recorded: [docs/transcripts/2026-08-31-deployed-checks-05-08-09.md](../../../docs/transcripts/2026-08-31-deployed-checks-05-08-09.md) — revision `93e79e6` on the public URL.
