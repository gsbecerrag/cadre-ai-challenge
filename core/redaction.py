"""The two Redaction Profiles: what may leave this process, and what never does.

Lifted from the adopted `pii-redaction` skill's deterministic pass-1 redactor
(`.claude/skills/pii-redaction/scripts/redact.py`), so the runtime depends on no skill folder
and on no new package: stdlib regex, plus the checksums that keep it honest — Luhn for cards,
mod-97 for IBANs, check digits for cédulas, RUCs, CPFs, RUTs and DNIs. A sixteen-digit number
that fails Luhn is an order number, and this leaves it alone. Microseconds per Turn, no model
call, and it cannot fail open the way a model can (ADR-0006).

`refuse` strips the **Refuse Set** — payment cards, bank accounts, government ids, credentials
and one-time codes, sensitive categories — and runs on the Visitor's message before the
provider call and before the message is stored. "Never echoed" and "never kept" then hold by
construction rather than by the model choosing well. **Contact Details** are untouched by it:
a work email and a phone number are what this product exists to collect.

`full` is `refuse` plus Contact Details tokenised — `[EMAIL_1]`, `[PHONE_1]`, the same value
always the same token within one text — and runs on everything that leaves the conversation
for somebody other than the Strategist handling it: log bodies now, Traces and notification
free text later.

Both return a `Redaction`: the rewritten text and a manifest of counts per category, never a
value. The counts ride to the Trace so that "how often do Visitors paste things they should
not" is a number nobody has to read a conversation to get.

Deliberate departures from the skill's script, all of them because this is a B2B AI
consultancy's support Assistant rather than a B2C support desk:

- `token` is domain vocabulary here ("our token budget"), so a bare `token` label no longer
  marks a credential; `access|bearer|auth|refresh token` and `api key` still do.
- `clave`, `código` and `pin` label a credential only when the value they introduce contains a
  digit, so "el factor clave es la velocidad" survives intact.
- English one-time-code labels ("verification code", "one-time code", "security code") were
  missing from the Spanish-first list and are added.
- A labelled government id with no check digit of its own — a Colombian cédula de ciudadanía,
  a passport, a driver's licence — is tagged on the strength of its label.
- Sensitive categories are tagged only where a Visitor states one about a person ("my
  diagnosis is …"), never on the bare word, so "our diagnosis workflow" is left alone.

Names, street addresses and quasi-identifiers need a model — the skill's pass 2 — and are
deferred: a Visitor's name still reaches a Trace in this phase (ADR-0006, known limitation).
"""

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Final, Literal

RedactionProfile = Literal["refuse", "full"]

# The categories `refuse` removes. Contact Details are not among them, by design.
REFUSE_SET: Final[tuple[str, ...]] = (
    "card",
    "iban",
    "ssn",
    "cedula",
    "ruc",
    "gov_id",
    "credential",
    "sensitive",
    "ip",
)

# What `full` adds on top of the Refuse Set: the Contact Details, tokenised rather than
# dropped, so redacted text stays readable.
CONTACT_DETAILS: Final[tuple[str, ...]] = ("email", "phone")


@dataclass(frozen=True)
class Redaction:
    """Redacted text and its manifest — `{category: count}`, never a value."""

    text: str
    counts: Mapping[str, int]


# ---------------------------------------------------------------------------- validators


def luhn_ok(digits: str) -> bool:
    """The payment-card checksum. Failing it is the usual sign of an order number."""
    total, alternate = 0, False
    for digit in reversed(digits):
        value = int(digit)
        if alternate:
            value *= 2
            if value > 9:
                value -= 9
        total += value
        alternate = not alternate
    return total % 10 == 0


def cedula_ok(digits: str) -> bool:
    """Ecuadorian cédula: province, third digit, and the tenth as a check digit."""
    if len(digits) != 10 or not digits.isdigit():
        return False
    province = int(digits[:2])
    if not (1 <= province <= 24 or province == 30):
        return False
    if int(digits[2]) > 5:
        return False
    total = 0
    for index, coefficient in enumerate([2, 1, 2, 1, 2, 1, 2, 1, 2]):
        product = int(digits[index]) * coefficient
        total += product - 9 if product > 9 else product
    return (10 - total % 10) % 10 == int(digits[9])


def ruc_ok(digits: str) -> bool:
    """Ecuadorian RUC: a natural person's cédula plus `001`, or a company's mod-11 check."""
    if len(digits) != 13 or not digits.isdigit() or not digits.endswith("001"):
        return False
    third = int(digits[2])
    if third <= 5:
        return cedula_ok(digits[:10])
    if third == 6:  # public entity: eight digits, a check digit, then 0001
        weights = [3, 2, 7, 6, 5, 4, 3, 2]
        total = sum(int(digits[index]) * weights[index] for index in range(8))
        check = 11 - total % 11
        check = 0 if check == 11 else check
        return check == int(digits[8]) and digits[9:] == "0001"
    if third == 9:  # private company
        weights = [4, 3, 2, 7, 6, 5, 4, 3, 2]
        total = sum(int(digits[index]) * weights[index] for index in range(9))
        check = 11 - total % 11
        check = 0 if check == 11 else check
        return check == int(digits[9])
    return False


def iban_ok(candidate: str) -> bool:
    """IBAN mod-97: the rearranged, letter-to-digit string leaves a remainder of one."""
    compact = candidate.replace(" ", "").upper()
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{11,30}", compact):
        return False
    rearranged = compact[4:] + compact[:4]
    return int("".join(str(int(char, 36)) for char in rearranged)) % 97 == 1


def cpf_ok(candidate: str) -> bool:
    """Brazilian CPF: two mod-11 check digits, and never eleven of the same digit."""
    digits = re.sub(r"\D", "", candidate)
    if len(digits) != 11 or digits == digits[0] * 11:
        return False
    for position in (9, 10):
        total = sum(int(digits[index]) * (position + 1 - index) for index in range(position))
        check = (total * 10) % 11
        check = 0 if check == 10 else check
        if check != int(digits[position]):
            return False
    return True


def rut_ok(candidate: str) -> bool:
    """Chilean RUT: mod-11 over cycling weights, with `K` for a remainder of ten."""
    compact = candidate.replace(".", "").replace("-", "").upper()
    body, verifier = compact[:-1], compact[-1]
    if not body.isdigit() or len(body) < 7:
        return False
    total, multiplier = 0, 2
    for char in reversed(body):
        total += int(char) * multiplier
        multiplier = 2 if multiplier == 7 else multiplier + 1
    remainder = 11 - total % 11
    expected = "0" if remainder == 11 else "K" if remainder == 10 else str(remainder)
    return verifier == expected


def dni_ok(candidate: str) -> bool:
    """Spanish DNI/NIE: the trailing letter is the number modulo twenty-three."""
    compact = candidate.upper().replace("-", "")
    letters = "TRWAGMYFPDXBNJZSQVHLCKE"
    match = re.fullmatch(r"([XYZ]?)(\d{7,8})([A-Z])", compact)
    if not match:
        return False
    prefix, number, letter = match.groups()
    number = {"X": "0", "Y": "1", "Z": "2"}.get(prefix, "") + number
    return letters[int(number) % 23] == letter


def ssn_ok(candidate: str) -> bool:
    """US SSN/ITIN: the ranges the Social Security Administration never issues."""
    digits = re.sub(r"\D", "", candidate)
    if len(digits) != 9:
        return False
    area, group, serial = int(digits[:3]), int(digits[3:5]), int(digits[5:])
    if area in (0, 666) or (area >= 900 and digits[0] != "9"):  # 9xx is an ITIN
        return False
    return group != 0 and serial != 0


# -------------------------------------------------------------------------------- rules

# A label that names a secret on its own: nothing else is written down after "password".
_STRONG_CREDENTIAL_LABEL = (
    r"password|passwd|passphrase|passcode|contrase[nñ]a"
    r"|cvv|cvc|otp"
    r"|one[- ]time (?:code|password|passcode|pin)"
    r"|verification code|security code|access code"
    r"|api[_ -]?key|secret key|(?:access|bearer|auth|refresh)[_ -]?token"
    r"|c[oó]digo de (?:verificaci[oó]n|seguridad|acceso)|clave de acceso"
)
_STRONG_CREDENTIAL = re.compile(
    rf"(?i)\b({_STRONG_CREDENTIAL_LABEL})\b(\s*(?:is|es|:|=)?\s*)([^\s,;]+)"
)

# A label that names a secret only sometimes: "el factor clave es la velocidad" is a sentence
# about latency. The value has to look like a code — that is, contain a digit — to count.
_WEAK_CREDENTIAL = re.compile(r"(?i)\b(pin|clave|c[oó]digo)\b(\s*(?:is|es|:|=)\s*)([^\s,;]+)")

_HIGH_ENTROPY_KEY = re.compile(
    r"\b(?:sk|pk|rk)_(?:live|test)_[A-Za-z0-9]{16,}\b|\b[A-Fa-f0-9]{32,}\b"
)

_SENSITIVE_TOPIC = (
    r"diagn[oó]stico|diagnosis|medical condition|health condition|condici[oó]n m[eé]dica"
    r"|medication|medicamento|disability|discapacidad|religion|religi[oó]n"
    r"|ethnicity|etnia|sexual orientation|orientaci[oó]n sexual"
    r"|union membership|afiliaci[oó]n sindical|criminal record|antecedentes penales"
    r"|immigration status|visa status|estado migratorio"
)
# Only where a Visitor states one about a person: the bare noun is ordinary business English
# ("our diagnosis workflow"), and tagging that would corrupt the question being asked.
_SENSITIVE = re.compile(
    rf"(?i)((?:my|our|his|her|their|mi|mis|nuestr[oa]|su)\s+(?:{_SENSITIVE_TOPIC})\b"
    r"\s*(?:is|are|es|son|:|=)\s*)([^.;,\n]+)"
)

_EMAIL = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    r"|(?i:[A-Za-z0-9_-]+(?:\s+(?:dot|punto)\s+[A-Za-z0-9_-]+)*\s+(?:at|arroba)\s+"
    r"[A-Za-z0-9-]+(?:\s+(?:dot|punto)\s+[A-Za-z0-9-]+)*\s+(?:dot|punto)\s+[A-Za-z]{2,4}\b)"
)

_IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){2,7}(?:[ ]?[A-Z0-9]{1,4})?\b")
# The label may sit a couple of words before the number: "our IBAN is ES91 …".
_IBAN_LABEL_BEFORE = re.compile(r"(?i)\biban\b\W*(?:is|es|:|=)?\W*$")

_CARD = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")
_THIRTEEN_DIGITS = re.compile(r"\b\d{13}\b")
_TEN_DIGITS = re.compile(r"\b\d{10}\b")
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CPF = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b\d{11}\b")
_RUT = re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b")
_CURP = re.compile(r"\b[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d\b")
_DNI = re.compile(r"\b[XYZ]?\d{7,8}-?[A-Z]\b")
_UK_NI = re.compile(
    r"\b(?!(?:D|F|I|Q|U|V)[A-Z]|[A-Z](?:D|F|I|O|Q|U|V))[A-Z]{2}\s?\d{2}\s?\d{2}\s?\d{2}\s?[A-D]\b"
)

# An id whose only validation is the word in front of it — a Colombian cédula de ciudadanía, a
# passport, a licence. Everything with a check digit has already been taken by the rules above.
_LABELLED_GOV_ID = re.compile(
    r"(?i)\b(c[ée]dula(?:\s+de\s+ciudadan[ií]a)?|documento\s+de\s+identidad|pasaporte|passport"
    r"|driver'?s\s+licen[cs]e|licencia\s+de\s+conducir|social\s+security(?:\s+number)?|ssn"
    r"|nit|dni|nie)\b"
    r"(\s*(?:es|is|no\.?|n[o°º]\.?|number|n[uú]mero|:|=)?\s*)"
    r"([A-Za-z]?\d[\d.\- ]{4,14}\d)"
)

_PHONE = re.compile(
    r"(?<![\w\[])(?:\+|00)[1-9]\d{0,2}[ .-]?(?:\(?\d{1,4}\)?[ .-]?){2,4}\d{2,4}\b"
    r"|\b0[2-79]\d{8}\b|\b0[2-79]\d[ .-]?\d{3}[ .-]?\d{4}\b"
    r"|\(?\b[2-9]\d{2}\)?[ .-]?[2-9]\d{2}[ .-]?\d{4}\b"
)

_IPV4 = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")

# An Ecuadorian SRI invoice number has a phone's shape and an id's length. It is operational
# data the Assistant may need, so it is lifted out of the text and put back at the end.
_INVOICE_NUMBER = re.compile(r"\b\d{3}-\d{3}-\d{9}\b")
_PLACEHOLDER = "\x00P{index}\x00"


class _Redactor:
    """One pass over one text. Token tables live here, so numbering is per text."""

    def __init__(self, profile: RedactionProfile) -> None:
        self._profile: RedactionProfile = profile
        self._counts: dict[str, int] = {}
        self._tokens: dict[str, dict[str, int]] = {"email": {}, "phone": {}}
        self._protected: list[str] = []

    # -- helpers

    def _count(self, category: str) -> None:
        self._counts[category] = self._counts.get(category, 0) + 1

    def _tag(self, category: str, tag: str) -> str:
        self._count(category)
        return tag

    def _token(self, category: str, value: str) -> str:
        """The same value always gets the same number inside one text."""
        normalised = re.sub(r"[\s\-().]", "", value.lower())
        if category == "phone":  # a number in local and international form is one number
            normalised = re.sub(r"^(?:\+|00)593", "0", normalised)
            normalised = re.sub(r"^(?:\+|00)1(?=\d{10}$)", "", normalised)
        table = self._tokens[category]
        if normalised not in table:
            table[normalised] = len(table) + 1
            self._count(category)
        return f"[{category.upper()}_{table[normalised]}]"

    # -- rules that need more than a constant replacement

    def _protect(self, match: re.Match[str]) -> str:
        self._protected.append(match.group(0))
        return _PLACEHOLDER.format(index=len(self._protected) - 1)

    def _credential(self, match: re.Match[str]) -> str:
        return f"{match.group(1)}{match.group(2)}{self._tag('credential', '[CREDENTIAL]')}"

    def _credential_if_it_looks_like_a_code(self, match: re.Match[str]) -> str:
        if not any(char.isdigit() for char in match.group(3)):
            return match.group(0)
        return self._credential(match)

    def _sensitive(self, match: re.Match[str]) -> str:
        return f"{match.group(1)}{self._tag('sensitive', '[SENSITIVE]')}"

    def _card(self, match: re.Match[str]) -> str:
        digits = re.sub(r"\D", "", match.group(0))
        if 13 <= len(digits) <= 19 and luhn_ok(digits) and digits[0] in "23456":
            self._count("card")
            return f"**** **** **** {digits[-4:]}"
        return match.group(0)

    def _iban(self, match: re.Match[str]) -> str:
        if not iban_ok(match.group(0)):
            return match.group(0)
        self._count("iban")
        last_four = re.sub(r"\s", "", match.group(0))[-4:]
        already_labelled = _IBAN_LABEL_BEFORE.search(match.string[: match.start()])
        return f"****{last_four}" if already_labelled else f"IBAN ****{last_four}"

    def _checked(
        self, category: str, tag: str, is_valid: Callable[[str], bool]
    ) -> Callable[[re.Match[str]], str]:
        def replace(match: re.Match[str]) -> str:
            return self._tag(category, tag) if is_valid(match.group(0)) else match.group(0)

        return replace

    def _labelled_gov_id(self, match: re.Match[str]) -> str:
        return f"{match.group(1)}{match.group(2)}{self._tag('gov_id', '[GOV_ID]')}"

    # -- the pass itself

    def run(self, text: str) -> Redaction:
        tokenise_contact_details = self._profile == "full"

        text = _INVOICE_NUMBER.sub(self._protect, text)
        text = _STRONG_CREDENTIAL.sub(self._credential, text)
        text = _WEAK_CREDENTIAL.sub(self._credential_if_it_looks_like_a_code, text)
        text = _HIGH_ENTROPY_KEY.sub(lambda _: self._tag("credential", "[CREDENTIAL]"), text)
        text = _SENSITIVE.sub(self._sensitive, text)
        if tokenise_contact_details:
            text = _EMAIL.sub(lambda match: self._token("email", match.group(0)), text)
        text = _IBAN.sub(self._iban, text)
        text = _CARD.sub(self._card, text)
        text = _THIRTEEN_DIGITS.sub(self._checked("ruc", "[RUC]", ruc_ok), text)
        text = _TEN_DIGITS.sub(self._checked("cedula", "[CEDULA]", cedula_ok), text)
        text = _SSN.sub(self._checked("ssn", "[SSN]", ssn_ok), text)
        text = _CPF.sub(self._checked("gov_id", "[GOV_ID]", cpf_ok), text)
        text = _RUT.sub(self._checked("gov_id", "[GOV_ID]", rut_ok), text)
        text = _CURP.sub(lambda _: self._tag("gov_id", "[GOV_ID]"), text)
        text = _DNI.sub(self._checked("gov_id", "[GOV_ID]", dni_ok), text)
        text = _UK_NI.sub(lambda _: self._tag("gov_id", "[GOV_ID]"), text)
        text = _LABELLED_GOV_ID.sub(self._labelled_gov_id, text)
        if tokenise_contact_details:
            text = _PHONE.sub(lambda match: self._token("phone", match.group(0)), text)
        text = _IPV4.sub(lambda _: self._tag("ip", "[IP]"), text)

        for index, original in enumerate(self._protected):
            text = text.replace(_PLACEHOLDER.format(index=index), original)
        return Redaction(text, self._counts)


def redact(text: str, profile: RedactionProfile) -> Redaction:
    """Apply one Redaction Profile to one text."""
    return _Redactor(profile).run(text)


def refuse(text: str) -> Redaction:
    """The `refuse` Redaction Profile: the Refuse Set out, Contact Details untouched.

    This is the Turn's pre-model, pre-store hook — the boundary at which a payment card stops
    existing anywhere the Visitor cannot see it.
    """
    return redact(text, "refuse")


def full(text: str) -> Redaction:
    """The `full` Redaction Profile: `refuse` plus Contact Details tokenised.

    The boundary for anything read by somebody other than the Strategist handling the Lead —
    log bodies, Traces, the free text of a notification.
    """
    return redact(text, "full")
