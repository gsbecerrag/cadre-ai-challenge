#!/usr/bin/env python3
"""Pass-1 PII redaction: structured identifiers only, with validation.

Usage:
    python redact.py input.txt [--manifest]
    echo "text" | python redact.py [--manifest]

Handles: emails, phones (intl/US/Ecuador), payment cards (Luhn), IBAN (mod-97),
SSN/ITIN, Ecuador cédula/RUC (check digit), Brazil CPF, Chile RUT, Mexico CURP,
Spain DNI/NIE, UK NI number, IPv4, labeled credentials/OTPs/CVVs.
Names, addresses, and contextual PII are left for the model (pass 2).

Redaction forms follow SKILL.md: cards/IBAN keep last 4; government IDs become
typed tags; emails/phones get numbered tokens consistent within the text.
"""
import json
import re
import sys

# ---------- validators ----------

def luhn_ok(digits: str) -> bool:
    total, alt = 0, False
    for d in reversed(digits):
        n = int(d)
        if alt:
            n *= 2
            if n > 9:
                n -= 9
        total += n
        alt = not alt
    return total % 10 == 0


def cedula_ok(d: str) -> bool:
    if len(d) != 10 or not d.isdigit():
        return False
    prov = int(d[:2])
    if not (1 <= prov <= 24 or prov == 30):
        return False
    if int(d[2]) > 5:
        return False
    coef = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    s = 0
    for i, c in enumerate(coef):
        p = int(d[i]) * c
        s += p - 9 if p > 9 else p
    return (10 - s % 10) % 10 == int(d[9])


def ruc_ok(d: str) -> bool:
    if len(d) != 13 or not d.isdigit() or not d.endswith("001"):
        return False
    third = int(d[2])
    if third <= 5:
        return cedula_ok(d[:10])
    if third == 6:  # public entity, 8 digits + check, then 0001
        w = [3, 2, 7, 6, 5, 4, 3, 2]
        s = sum(int(d[i]) * w[i] for i in range(8))
        chk = 11 - s % 11
        chk = 0 if chk == 11 else chk
        return chk == int(d[8]) and d[9:] == "0001"
    if third == 9:  # private company
        w = [4, 3, 2, 7, 6, 5, 4, 3, 2]
        s = sum(int(d[i]) * w[i] for i in range(9))
        chk = 11 - s % 11
        chk = 0 if chk == 11 else chk
        return chk == int(d[9])
    return False


def iban_ok(s: str) -> bool:
    s = s.replace(" ", "").upper()
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{11,30}", s):
        return False
    r = s[4:] + s[:4]
    num = "".join(str(int(c, 36)) for c in r)
    return int(num) % 97 == 1


def cpf_ok(d: str) -> bool:
    d = re.sub(r"\D", "", d)
    if len(d) != 11 or d == d[0] * 11:
        return False
    for n in (9, 10):
        s = sum(int(d[i]) * (n + 1 - i) for i in range(n))
        chk = (s * 10) % 11
        chk = 0 if chk == 10 else chk
        if chk != int(d[n]):
            return False
    return True


def rut_ok(s: str) -> bool:
    s = s.replace(".", "").replace("-", "").upper()
    body, dv = s[:-1], s[-1]
    if not body.isdigit() or len(body) < 7:
        return False
    total, mult = 0, 2
    for c in reversed(body):
        total += int(c) * mult
        mult = 2 if mult == 7 else mult + 1
    r = 11 - total % 11
    exp = "0" if r == 11 else "K" if r == 10 else str(r)
    return dv == exp


def dni_ok(s: str) -> bool:
    s = s.upper().replace("-", "")
    letters = "TRWAGMYFPDXBNJZSQVHLCKE"
    m = re.fullmatch(r"([XYZ]?)(\d{7,8})([A-Z])", s)
    if not m:
        return False
    pre, num, let = m.groups()
    num = {"X": "0", "Y": "1", "Z": "2"}.get(pre, "") + num
    return letters[int(num) % 23] == let


def ssn_ok(d: str) -> bool:
    d = re.sub(r"\D", "", d)
    if len(d) != 9:
        return False
    a, g, s = int(d[:3]), int(d[3:5]), int(d[5:])
    if a in (0, 666) or a >= 900 and d[0] != "9":  # allow ITIN 9xx
        return False
    return g != 0 and s != 0


# ---------- rules (order matters: longer/more specific first) ----------

class Redactor:
    def __init__(self):
        self.counts = {}
        self.tokens = {"EMAIL": {}, "PHONE": {}}

    def _count(self, kind):
        self.counts[kind] = self.counts.get(kind, 0) + 1

    def _numbered(self, kind, value):
        norm = re.sub(r"[\s\-().]", "", value.lower())
        if kind == "PHONE":  # same number in local vs intl form → same token
            norm = re.sub(r"^(\+|00)593", "0", norm)
            norm = re.sub(r"^(\+|00)1(?=\d{10}$)", "", norm)
        table = self.tokens[kind]
        if norm not in table:
            table[norm] = len(table) + 1
            self._count(kind)
        return f"[{kind}_{table[norm]}]"

    def _iban(self, m):
        self._count("IBAN")
        last4 = re.sub(r"\s", "", m.group(0))[-4:]
        labeled = re.search(r"(?i)iban\W*$", m.string[:m.start()])
        return f"****{last4}" if labeled else f"IBAN ****{last4}"

    def run(self, text: str) -> str:
        # protect operational formats that look like phones/IDs (Ecuador SRI invoice 001-002-000012345)
        protected = []
        def _protect(m):
            protected.append(m.group(0))
            return f"\x00P{len(protected)-1}\x00"
        text = re.sub(r"\b\d{3}-\d{3}-\d{9}\b", _protect, text)
        # credentials by label (password/otp/pin/cvv/clave/contraseña/código)
        text = re.sub(
            r"(?i)\b(password|passwd|contraseña|clave|pin|otp|cvv|cvc|c[oó]digo(?: de)? (?:verificaci[oó]n|seguridad)|api[_ -]?key|token)\b(\s*(?:is|es|:|=)?\s*)([^\s,;]+)",
            lambda m: (self._count("CREDENTIAL"), f"{m.group(1)}{m.group(2)}[CREDENTIAL]")[1],
            text,
        )
        # high-entropy keys
        text = re.sub(
            r"\b(sk|pk|rk)_(live|test)_[A-Za-z0-9]{16,}\b|\b[A-Fa-f0-9]{32,}\b",
            lambda m: (self._count("CREDENTIAL"), "[CREDENTIAL]")[1],
            text,
        )
        # emails (incl. obfuscated "at"/"dot")
        text = re.sub(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|(?i:[A-Za-z0-9_-]+(?:\s+(?:dot|punto)\s+[A-Za-z0-9_-]+)*\s+(?:at|arroba)\s+[A-Za-z0-9-]+(?:\s+(?:dot|punto)\s+[A-Za-z0-9-]+)*\s+(?:dot|punto)\s+[A-Za-z]{2,4}\b)",
            lambda m: self._numbered("EMAIL", m.group(0)),
            text,
        )
        # IBAN
        text = re.sub(
            r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){2,7}(?:[ ]?[A-Z0-9]{1,4})?\b",
            lambda m: self._iban(m) if iban_ok(m.group(0)) else m.group(0),
            text,
        )
        # payment cards (13-19 digits, groups) with Luhn
        def card(m):
            digits = re.sub(r"\D", "", m.group(0))
            if 13 <= len(digits) <= 19 and luhn_ok(digits) and digits[0] in "23456":
                self._count("CARD")
                return f"**** **** **** {digits[-4:]}"
            return m.group(0)
        text = re.sub(r"\b(?:\d[ -]?){12,18}\d\b", card, text)
        # Ecuador RUC (13) then cédula (10)
        text = re.sub(r"\b\d{13}\b", lambda m: (self._count("RUC"), "[RUC]")[1] if ruc_ok(m.group(0)) else m.group(0), text)
        text = re.sub(r"\b\d{10}\b", lambda m: (self._count("CEDULA"), "[CEDULA]")[1] if cedula_ok(m.group(0)) else m.group(0), text)
        # SSN / ITIN
        text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", lambda m: (self._count("SSN"), "[SSN]")[1] if ssn_ok(m.group(0)) else m.group(0), text)
        # Brazil CPF
        text = re.sub(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b\d{11}\b", lambda m: (self._count("GOV_ID"), "[GOV_ID]")[1] if cpf_ok(m.group(0)) else m.group(0), text)
        # Chile RUT
        text = re.sub(r"\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b", lambda m: (self._count("GOV_ID"), "[GOV_ID]")[1] if rut_ok(m.group(0)) else m.group(0), text)
        # Mexico CURP
        text = re.sub(r"\b[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d\b", lambda m: (self._count("GOV_ID"), "[GOV_ID]")[1], text)
        # Spain DNI / NIE
        text = re.sub(r"\b[XYZ]?\d{7,8}-?[A-Z]\b", lambda m: (self._count("GOV_ID"), "[GOV_ID]")[1] if dni_ok(m.group(0)) else m.group(0), text)
        # UK NI number
        text = re.sub(r"\b(?!(?:D|F|I|Q|U|V)[A-Z]|[A-Z](?:D|F|I|O|Q|U|V))[A-Z]{2}\s?\d{2}\s?\d{2}\s?\d{2}\s?[A-D]\b", lambda m: (self._count("GOV_ID"), "[GOV_ID]")[1], text)
        # phones: intl +CC, Ecuador 09x/0[2-7], US
        text = re.sub(
            r"(?<![\w\[])(?:\+|00)[1-9]\d{0,2}[ .-]?(?:\(?\d{1,4}\)?[ .-]?){2,4}\d{2,4}\b"
            r"|\b0[2-79]\d{8}\b|\b0[2-79]\d[ .-]?\d{3}[ .-]?\d{4}\b"
            r"|\(?\b[2-9]\d{2}\)?[ .-]?[2-9]\d{2}[ .-]?\d{4}\b",
            lambda m: self._numbered("PHONE", m.group(0)),
            text,
        )
        # IPv4
        text = re.sub(
            r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b",
            lambda m: (self._count("IP"), "[IP]")[1],
            text,
        )
        for i, v in enumerate(protected):
            text = text.replace(f"\x00P{i}\x00", v)
        return text


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    manifest = "--manifest" in sys.argv
    text = open(args[0], encoding="utf-8").read() if args else sys.stdin.read()
    r = Redactor()
    out = r.run(text)
    sys.stdout.write(out)
    if manifest:
        sys.stdout.write("\n\n" + json.dumps({"redacted": r.counts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
