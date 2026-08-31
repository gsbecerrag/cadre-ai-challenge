"""Who is allowed into the Console — seam S2, pure units.

Two decisions live here and nowhere else: what a Firebase ID token's claims mean (which
Strategist is this?) and whether that Strategist is on the allowlist (may they see Leads?).
Both are pure, both are the only thing standing between a public URL and every Lead the
Assistant ever captured (ADR-0010), so they are pinned here rather than inferred from an HTTP
test.

Every email is obviously fake.
"""

import pytest

from core.auth import (
    InvalidTokenError,
    StrategistIdentity,
    identity_from_claims,
    is_allowlisted,
    parse_allowlist,
)

# What Firebase puts in a Google sign-in ID token, trimmed to the claims we read.
GOOGLE_CLAIMS = {
    "sub": "uid-strategist-0001",
    "email": "angel@example.com",
    "email_verified": True,
    "name": "Angel M.",
}


def test_the_allowlist_is_a_comma_separated_list_of_emails_compared_case_insensitively() -> None:
    """`ADMIN_ALLOWED_EMAILS` is typed by a human into a deploy command, so spacing and case
    are theirs to get wrong and ours to normalise. A Strategist locked out of the Console by a
    capital letter would be diagnosed as a broken sign-in."""
    allowlist = parse_allowlist(" Angel@Example.com ,strategist@example.com,, ")

    assert allowlist == frozenset({"angel@example.com", "strategist@example.com"})
    assert is_allowlisted("ANGEL@example.com", allowlist) is True
    assert is_allowlisted("  angel@example.com  ", allowlist) is True
    assert is_allowlisted("visitor@example.com", allowlist) is False


def test_an_empty_allowlist_admits_nobody() -> None:
    """The failure mode that matters: a deploy that forgets `ADMIN_ALLOWED_EMAILS` must close
    the Console, not open it. An unset variable is the most likely mistake in this system, and
    the blast radius is every Lead's Contact Details."""
    assert parse_allowlist("") == frozenset()
    assert is_allowlisted("angel@example.com", parse_allowlist("")) is False


def test_a_google_sign_in_claim_set_becomes_the_strategist_who_signed_in() -> None:
    assert identity_from_claims(GOOGLE_CLAIMS) == StrategistIdentity(
        uid="uid-strategist-0001", email="angel@example.com", name="Angel M."
    )


def test_the_strategist_email_is_normalised_so_the_allowlist_check_cannot_be_case_dodged() -> None:
    identity = identity_from_claims({**GOOGLE_CLAIMS, "email": " Angel@Example.com "})

    assert identity.email == "angel@example.com"


def test_a_strategist_with_no_name_claim_is_named_by_the_local_part_of_their_email() -> None:
    """The Console header shows a name and an avatar initial; an empty header is a bug report."""
    identity = identity_from_claims(
        {key: GOOGLE_CLAIMS[key] for key in GOOGLE_CLAIMS if key != "name"}
    )

    assert identity.name == "angel"


def test_a_claim_set_with_no_verified_email_is_not_an_identity() -> None:
    """The allowlist is a list of emails, so an unverified email claim is an allowlist bypass:
    an account created against another provider could assert a Cadre address it does not own."""
    with pytest.raises(InvalidTokenError):
        identity_from_claims({**GOOGLE_CLAIMS, "email_verified": False})

    with pytest.raises(InvalidTokenError):
        identity_from_claims(
            {key: GOOGLE_CLAIMS[key] for key in GOOGLE_CLAIMS if key != "email_verified"}
        )


def test_a_claim_set_with_no_email_or_no_subject_is_not_an_identity() -> None:
    with pytest.raises(InvalidTokenError):
        identity_from_claims({**GOOGLE_CLAIMS, "email": ""})

    with pytest.raises(InvalidTokenError):
        identity_from_claims({**GOOGLE_CLAIMS, "sub": ""})
