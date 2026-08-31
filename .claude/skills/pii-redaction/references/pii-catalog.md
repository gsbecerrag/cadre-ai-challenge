# PII catalog — formats, validation, redaction form

Use this when applying pass 1 manually (no code execution) or when deciding whether an ambiguous string is PII. Validation rules exist to avoid over-firing on order numbers, amounts, and dates.

## Generic

| Type | Format | Validation / disambiguation | Redact as |
|---|---|---|---|
| Email | `local@domain.tld`; also obfuscated "juan at gmail dot com" | — | `[EMAIL_n]` |
| Phone (intl) | `+CC` then 6–14 digits, with optional spaces/dashes/parens | Leading `+` or `00` and a plausible country code | `[PHONE_n]` |
| Payment card | 13–19 digits, often grouped 4-4-4-4 or 4-6-5 (Amex) | **Luhn checksum must pass.** Prefixes: 4 Visa, 51–55/2221–2720 MC, 34/37 Amex, 6011/65 Discover. If Luhn fails → likely not a card (order/tracking no.) | `**** **** **** 4417` (last 4 kept) |
| Card expiry + CVV | `MM/YY` near a card; 3–4 digits labeled cvv/cvc/código | Only when adjacent to card context | `[CREDENTIAL]` |
| IBAN | 2 letters + 2 check digits + up to 30 alphanumerics (`ES91 2100 0418 4502 0005 1332`) | Mod-97 check on the rearranged string = 1 | `IBAN ****1332` |
| Password / OTP / PIN / API key | Labeled ("contraseña", "password", "clave", "código de verificación", "pin"); long random strings (`sk_live_…`, 32+ hex) | Context label or high-entropy string | `[CREDENTIAL]` |
| DOB | Any date labeled as birth date, or date + age math | Label or context; plain dates are not DOBs | `[DOB]` |
| IPv4 / IPv6 | `192.168.1.1` / colon-hex | Octets 0–255 | `[IP]` |
| MAC / IMEI / device ID | `AA:BB:CC:DD:EE:FF` / 15 digits labeled IMEI | Label or format | `[DEVICE_ID]` |
| License plate | Country-specific; Ecuador `ABC-1234` / `ABC-123` | Format + context | `[PLATE]` |
| Street address | Number + street name, or named building + floor/apt | Contextual | `[ADDRESS]` (keep city) |
| Names | Contextual (pass 2) | Not company/product/public-role | `[PERSON_n]` |

## United States

| Type | Format | Validation | Redact as |
|---|---|---|---|
| SSN | `AAA-GG-SSSS`, sometimes no dashes | Area ≠ 000, 666, 900–999; group ≠ 00; serial ≠ 0000 | `[SSN]` |
| ITIN | `9XX-XX-XXXX`, 4th digit 7 or 8 | Starts with 9 | `[SSN]` |
| Phone | `(NXX) NXX-XXXX`, `NXX-NXX-XXXX`, `+1 …` | Area and exchange start 2–9 | `[PHONE_n]` |
| ZIP | 5 digits; ZIP+4 `12345-6789` | Bare 5-digit ZIP alone is not PII; ZIP+4 or ZIP + street → redact with address | part of `[ADDRESS]` |
| Driver's license | State-specific alphanumerics, labeled | Label | `[GOV_ID]` |
| Passport | 9 digits (or letter + 8) labeled | Label | `[PASSPORT]` |

## Ecuador

| Type | Format | Validation | Redact as |
|---|---|---|---|
| Cédula | 10 digits | Digits 1–2 = province 01–24 or 30 (foreigners); digit 3 ∈ 0–5; **check digit (10th)**: multiply digits 1–9 by 2,1,2,1,2,1,2,1,2; if a product > 9 subtract 9; sum; check = (10 − sum mod 10) mod 10 | `[CEDULA]` |
| RUC (natural person) | 13 digits = valid cédula + `001` | First 10 pass cédula check; last 3 = `001` | `[RUC]` |
| RUC (company/public) | 13 digits, digit 3 = 6 (public) or 9 (private), ends `001` | Mod-11 check with weights 3,2,7,6,5,4,3,2 (public, 8 digits) or 4,3,2,7,6,5,4,3,2 (private, 9 digits) | `[RUC]` — company RUCs are less sensitive but redact by default in customer text |
| Mobile | `09X XXX XXXX` (10 digits starting 09) or `+593 9X XXX XXXX` | Starts 09 / +5939 | `[PHONE_n]` |
| Landline | `0[2-7] XXX XXXX` or `+593 [2-7] XXX XXXX` | Area code 2–7 | `[PHONE_n]` |
| Passport | Letter + 7 digits typically, labeled | Label | `[PASSPORT]` |
| Plate | `ABC-1234` (cars), `ABC-123` older | Format | `[PLATE]` |

## EU / LatAm (broad)

| Country | ID | Format | Validation | Redact as |
|---|---|---|---|---|
| Spain | DNI | 8 digits + letter | Letter = `TRWAGMYFPDXBNJZSQVHLCKE`[number mod 23] | `[GOV_ID]` |
| Spain | NIE | X/Y/Z + 7 digits + letter | Replace X/Y/Z with 0/1/2, then DNI rule | `[GOV_ID]` |
| Mexico | CURP | 18 alphanumerics (4 letters, 6 digits DOB, H/M, 5 letters, 2 alnum) | Pattern; contains DOB → also `[DOB]`-class | `[GOV_ID]` |
| Mexico | RFC | 4 letters + 6 digits + 3 alnum (persons); 3 letters + 6 + 3 (companies) | Pattern | `[GOV_ID]` |
| Brazil | CPF | `XXX.XXX.XXX-XX` or 11 digits | Two mod-11 check digits; reject all-same-digit | `[GOV_ID]` |
| Brazil | CNPJ | `XX.XXX.XXX/XXXX-XX` | Mod-11 | `[GOV_ID]` (company; lower sensitivity) |
| Chile | RUT | `XX.XXX.XXX-K` (K = digit or K) | Mod-11 with weights 2–7 cycling; remainder 11→0, 10→K | `[GOV_ID]` |
| Colombia | Cédula de ciudadanía | 6–10 digits, labeled | Label + context | `[GOV_ID]` |
| Peru | DNI | 8 digits, labeled | Label | `[GOV_ID]` |
| Argentina | DNI / CUIL | 7–8 digits / `XX-XXXXXXXX-X` | CUIL mod-11 | `[GOV_ID]` |
| UK | National Insurance no. | `AB 12 34 56 C` | Prefix not D/F/I/Q/U/V; second letter not O; suffix A–D | `[GOV_ID]` |
| UK | NHS number | 10 digits, `XXX XXX XXXX` | Mod-11 | `[GOV_ID]` + `[SENSITIVE]` |
| Italy | Codice fiscale | 16 alphanumerics | Pattern | `[GOV_ID]` |
| France | NIR (sécu) | 15 digits, starts 1/2 | Mod-97 | `[GOV_ID]` |
| Germany | Steuer-ID | 11 digits | Pattern | `[GOV_ID]` |
| EU | IBAN | See generic | Mod-97 | `IBAN ****XXXX` |
| EU | Phone | `+CC …` | Country code | `[PHONE_n]` |

## Sensitive categories (always `[SENSITIVE]`, regardless of format)

Health conditions, medications, diagnoses; biometric data; racial/ethnic origin; religion; political opinions; sexual orientation or life; union membership; criminal records or allegations; immigration status. These aren't identifiers by themselves, but combined with any identifier they are the highest-harm class. Redact the sensitive detail even when the person is already tokenized.

## Not PII (keep unless explicitly scrubbing for external export)

Order/ticket/invoice/tracking numbers · SKUs · amounts and currencies · non-birth dates · company names · product names · generic city/country names · bare 5-digit ZIP · bare age · job titles without employer · public figures in public roles · already-masked values (`****4417`, `[PERSON_1]`).
