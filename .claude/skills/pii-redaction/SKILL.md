---
name: pii-redaction
description: Detect and redact personally identifiable information (PII) in text, and enforce PII-handling guardrails when acting as a customer-facing chat agent. Covers generic identifiers (names, emails, phones, addresses, DOB, payment cards, credentials), US (SSN, phones, ZIP+4), Ecuador (cédula, RUC, +593 phones), and broad EU/LatAm IDs (IBAN, DNI/NIE, CURP/RFC, CPF, RUT, NI number). Use this skill whenever text needs to be scrubbed before logging, storing, forwarding, summarizing, or displaying — transcripts, tickets, CRM notes, tool-call payloads, analytics — and whenever an agent is talking to customers and PII appears in either direction. Trigger even when the user just says "clean this up before I save it", "anonymize", "mask", "strip personal data", or "is it safe to send this?", and in any customer-facing session where a person shares identifiers.
---

# PII Redaction

Two jobs, one skill:

1. **Redact mode** — given text, return the same text with PII replaced, using a redaction form that depends on the type (mask financial numbers, tag names with consistent tokens, drop government IDs entirely).
2. **Guardrail mode** — while acting as a customer-facing agent, handle PII the customer shares without echoing it, without requesting more than needed, and without letting it leak into notes, tickets, tool calls, or summaries.

Redact mode is what you *do to text*. Guardrail mode is how you *behave*. In a customer-facing session both are active: guardrails govern the conversation, and redact mode runs on everything that leaves the conversation.

The bias is toward recall: **if something could reasonably identify a person, treat it as PII.** Over-redacting a city name costs little; leaking a cédula costs a lot. But redaction must never make the agent useless — that's what consistent tokens and partial masks are for.

## Redaction forms by type

| Type | Form | Example |
|---|---|---|
| Person names | Consistent numbered token | `[PERSON_1]`, `[PERSON_2]` — same person → same token throughout |
| Emails | Numbered token | `[EMAIL_1]` |
| Phones (any country) | Numbered token | `[PHONE_1]` |
| Payment cards | **Mask, keep last 4** | `**** **** **** 4417` |
| Bank accounts / IBAN | **Mask, keep last 4** | `IBAN ****1234` |
| Government IDs (SSN, cédula, RUC, passport, DNI, NIE, CURP, RFC, CPF, RUT, NI no., driver's license) | **Typed tag, no digits kept** | `[SSN]`, `[CEDULA]`, `[RUC]`, `[PASSPORT]`, `[GOV_ID]` |
| Credentials (passwords, OTPs, PINs, API keys, security answers) | Typed tag, no chars kept | `[CREDENTIAL]` |
| Street addresses | Typed tag; city/country may stay | `[ADDRESS], Quito` |
| Dates of birth | Typed tag | `[DOB]` (a bare age like "34" is fine alone) |
| IP addresses, device IDs, MAC, IMEI, license plates | Typed tag | `[IP]`, `[DEVICE_ID]`, `[PLATE]` |
| Health, biometric, religion, sexual orientation, union, criminal details | Typed tag | `[SENSITIVE]` |
| URLs containing a person's identifiers (profile links, tracking links with emails) | Typed tag | `[URL]` |
| Employer / school / small organization, when it narrows to a person | Typed tag | `[ORG]` — company names in a business context stay. **In this repository company names always stay** (see the Cadre AI adaptation below) |

**Why the split**: last-4 on cards/accounts is the industry-standard reference that lets a conversation continue ("the card ending in 4417") without being usable for fraud. Government IDs have no safe partial form — a partial cédula still narrows to one person. Names get tokens rather than blanks so the redacted text stays readable: "[PERSON_1] said [PERSON_2] would pay" is useful; "[NAME] said [NAME] would pay" is not.

**Operational identifiers stay by default**: order numbers, ticket IDs, SKUs, invoice numbers, tracking numbers, amounts, dates that aren't DOBs. These are what the agent needs to do its job. Redact them only when explicitly scrubbing for external sharing (analytics export, sharing outside the company) — ask if unclear.

## Redact mode — workflow

### Pass 1: structured identifiers (deterministic)

If code execution is available, run `scripts/redact.py`:

```
python scripts/redact.py input.txt              # writes redacted text to stdout
python scripts/redact.py input.txt --manifest   # also prints a JSON count of what was redacted, by type
echo "text" | python scripts/redact.py          # stdin works too
```

It handles emails, phones (US, Ecuador, international +CC), payment cards (Luhn-validated), SSN, Ecuador cédula/RUC (check-digit validated), IBAN, Brazil CPF, Chile RUT, Mexico CURP, Spain DNI/NIE, UK NI number, IPv4, and credential patterns. Validation matters: a Luhn-failing 16-digit number is probably an order number, not a card — the script leaves it.

If code execution is NOT available, apply the same patterns manually using `references/pii-catalog.md`, which lists every format with its validation rule.

### Pass 2: contextual PII (you)

Regex can't find names, addresses, or "my daughter's school is Colegio Americano." Read the pass-1 output and redact:

- **Names** — of the customer, their family, coworkers, anyone. Not company names, product names, or public figures acting in public roles. Assign `[PERSON_n]` tokens in order of first appearance and keep them consistent.
- **Addresses** — anything street-level. Keep city/region/country unless it's tiny enough to identify someone (a village) or is combined with other quasi-identifiers.
- **Quasi-identifier combinations** — employer + job title + city, or "the only Ecuadorian nurse at Hospital X." Individually harmless, together identifying. Redact the piece that does the most narrowing.
- **Indirect references** — "my account under my wife's name, Marcela" → `[PERSON_2]`; "the number on the back of my card, 847" → `[CREDENTIAL]`.
- **Anything pass 1 missed** — unusual formatting ("my email is juan at gmail dot com"), spelled-out numbers, IDs with spaces or dashes in odd places.

### Pass 3: sanity check

- Read the result as a stranger. Can you identify anyone? If yes, go again.
- Read it as the agent who needs to act on it. Is the task still doable? If a needed operational ID got redacted, restore it.
- Check token consistency: one person, one token.

### Output

Return the redacted text. If the user asked for it, or if the redaction is going into a pipeline, append a compact manifest:

```
Redacted: 2 names, 1 email, 1 phone, 1 card (masked), 1 cédula
```

Never include the original values in the manifest.

## Guardrail mode — behavior in customer-facing sessions

These apply the moment PII appears in a customer conversation, in either direction.

**Don't echo.** When a customer shares a full card number, ID, or password, never repeat it back — not even to confirm. Confirm with the masked form: "Got it — I'll update the card ending in 4417." If they share a password or OTP, say plainly that they shouldn't share it in chat and that you won't use it, then continue the task another way.

**Ask for the minimum.** Verification needs the last 4 of something, a ZIP code, or an order number — not a full SSN or cédula. If the workflow genuinely requires a full government ID, route the customer to the secure form/channel designed for it rather than collecting it in chat. Never ask for a full payment card number in chat.

**Redact before it leaves the conversation.** Every ticket, CRM note, summary, escalation message, search query, and tool-call payload is run through redact mode first — unless the specific field is designed to hold that data (a `card_last4` field takes last 4; a `notes` free-text field takes redacted text). When in doubt, the free-text field gets the redacted version.

**Never surface other people's PII.** If a lookup returns another customer's record, or a customer asks about someone else's account, don't reveal it. "I can only discuss the account you're verified on."

**Keep working.** Guardrails restrict what you *repeat and store*, not what you *do*. Use the customer's PII in-session to do the job — look up the order, update the address — then reference it in masked/token form everywhere else. A guardrail that makes you refuse to help is a broken guardrail.

**Language-agnostic.** Customers write in Spanish, English, Portuguese, mixed. PII is PII in any language; "mi cédula es…" and "my SSN is…" get identical handling.

### Example — customer shares too much

> Customer: hola, quiero cambiar la tarjeta de mi cuenta. la nueva es 4532 0151 2345 4417, vence 08/28, cvv 213. mi cédula es 1712345678 por si necesitan.

Agent response (correct):

> ¡Hola! Con gusto te ayudo. Un par de cosas primero: por seguridad, no compartas el CVV ni la cédula completa por chat — no los voy a usar y te recomiendo borrarlos del historial si puedes. Para actualizar la tarjeta terminada en **4417**, te envío un enlace seguro donde puedes ingresarla directamente. [continues with the task]

Ticket note written by the agent (correct):

> Customer requested card update. Shared full card + CVV + cédula in chat (advised not to). Sent secure update link for card ending 4417. No further verification needed.

What the agent must NOT do: repeat the full number "to confirm", write the card or cédula into the note, or refuse the whole request because PII was shared.

## Edge cases

- **Customer insists you confirm the full number**: still don't. Offer last 4 plus expiry month as confirmation.
- **PII inside a document/screenshot the customer uploads**: same rules — extract what's needed for the task, redact in any output.
- **Test/sample data**: if the user says data is synthetic, still redact by default (you can't verify), but skip the "don't share this" lecture.
- **Public figures**: a politician's name in a news context isn't PII to redact; the same name as a customer is. Judge by role in the text.
- **Ambiguous numbers**: a 10-digit number could be a cédula, a US phone, or an order number. Use validation (cédula check digit, phone formatting) and context ("orden #", "pedido"). If still ambiguous, redact — recall over precision.
- **Already-masked data**: `****4417` and `[PERSON_1]` pass through unchanged.

## Cadre AI adaptation (B2B support agent)

This repository's Assistant talks to business prospects, and the product exists to collect a Lead's **Contact Details** (name, work email, phone, company, role — see `CONTEXT.md`). The generic rules above were written for B2C support; these refinements override them here:

- **Contact Details are welcome, never lectured about.** When a Visitor shares a work email or phone, the Assistant captures it into the Lead and thanks them. The "please don't share that here" response is reserved for the **Refuse Set**: payment cards, bank accounts/IBAN, government IDs, credentials/OTPs, and sensitive categories. For those: don't echo, say they aren't needed, continue the task.
- **Company names always stay.** The company is the lead; the `[ORG]` rule never applies to it.
- **Confidential business data is not PII.** Revenue figures, client lists, internal plans a Visitor pastes are not redacted — but the Assistant does not need them: "You don't need to share internal figures with me — a strategist will cover that under NDA," then moves on.
- **Two Redaction Profiles, applied at fixed boundaries:**
  - `refuse` — the Refuse Set only. Runs **before the model call** and **before any message is stored**, so "don't echo" and "don't store" hold by construction.
  - `full` — the Refuse Set plus emails and phones tokenized (`[EMAIL_1]`, `[PHONE_1]`). Runs on everything that leaves the conversation for people other than the Strategist handling it: traces, logs, and the free-text part of notifications.
  - The Lead's typed Contact Details fields and the Strategist-facing contact block are **never** redacted — they are "fields designed to hold that data".
- **Pass 1 only in the MVP.** The deterministic `scripts/redact.py` logic is the runtime module; the model-driven pass 2 (names, addresses, quasi-identifiers) is deferred, so Visitor *names* remain in traces for now. Stated as a known limitation.
- **Manifest counts are a metric.** The `--manifest` counts of each Turn are attached to its Trace, so "how often do Visitors paste things they shouldn't" is a dashboard number.
