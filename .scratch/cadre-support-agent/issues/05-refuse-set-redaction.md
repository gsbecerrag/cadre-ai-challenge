# 05: The Refuse Set never reaches the model or storage

**What to build:** A Visitor who pastes a payment card, a government id, a password, or a one-time code is told plainly that it is not needed and will not be kept, and the conversation continues — while the raw value never reaches the model, Firestore, or a log line. This slice lifts the adopted redaction skill's deterministic redactor into the core package as the runtime module with the two Redaction Profiles: `refuse` (cards masked to last four, IBAN masked, government ids and credentials replaced by typed tags, sensitive categories tagged) applied to every Visitor message before the provider call and before the message is stored; `full` (`refuse` plus emails and phones tokenised with consistent numbered tokens) applied to log bodies and, later, to Traces and notifications. Contact Details are not touched by `refuse`. The system prompt gains the guardrail rules from the skill's B2B adaptation (Contact Details welcomed, Refuse Set declined without echoing, confidential business data politely declined). Per-Turn redaction counts are recorded on the Turn for later tagging. Phase P1.

**Blocked by:** 02 (First Turn end-to-end with the stub provider)

**Status:** in-progress

- [ ] The `refuse` profile masks a Luhn-valid card to its last four, tags a valid SSN and a valid cédula, tags a labelled password, and leaves an order-like number, an email, and a phone untouched; the `full` profile additionally tokenises emails and phones consistently within one text; covered at seam S2 with fixtures from the skill's catalog (fake values only).
- [ ] A Visitor message containing a card number reaches the stub provider already masked and is stored masked; covered at seam S1 by inspecting what the stub received and what the in-memory store holds.
- [ ] Debug-level log bodies pass through the `full` profile; covered at S2 with a captured log record.
- [ ] The Turn's redaction counts are available on the Turn result (for the Trace tag in a later ticket); covered at S1.
- [ ] Manual check on the deployed app: pasting a fake card number yields the "not needed, not kept" reply and the Firestore message shows the masked form; recorded in the PR.
