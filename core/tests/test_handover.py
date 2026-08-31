"""The Handover Request's state machine — seam S2, pure and exhaustive.

A Hand-over is the one part of the product where a Strategist's time is spent, so the states
are not decoration: they decide whether a Visitor is told somebody is joining, whether the
Console shows a request as work to pick up, and whether a second click can move a request that
has already ended. Every transition is validated server-side (ADR-0007), which only means
anything if the table below is the whole table — hence the exhaustive 8x8 sweep rather than a
few happy paths.

Every personal value here is obviously fake.
"""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from core.handover import (
    HANDOVER_STATES,
    HandoverMode,
    HandoverRequest,
    HandoverState,
    InvalidTransitionError,
    LeadSnapshot,
    join_timed_out,
    may_transition,
    new_request_id,
    transition,
)
from core.store import Lead, lead_snapshot
from core.video import room_name

# The machine the spec names, written out again rather than imported: a test that reads the
# production table would agree with any mistake made in it.
ALLOWED: frozenset[tuple[str, str]] = frozenset(
    {
        ("offered", "accepted_by_user"),
        ("offered", "declined"),
        ("accepted_by_user", "pending_strategist"),
        ("pending_strategist", "strategist_joined"),
        ("pending_strategist", "no_strategist_available"),
        ("strategist_joined", "in_call"),
        ("in_call", "ended"),
    }
)

QUALIFIED_LEAD = LeadSnapshot(
    name="Jane Doe",
    email="jane@example.com",
    company="Acme Manufacturing",
    phone="+1 555 0100",
    role="VP of Operations",
    signals={
        "industry_fit": "Manufacturing & Logistics",
        "company_size_or_role": "VP of Operations at roughly 300 people",
        "initiative_or_pain": "supplier paperwork eats three days a week",
    },
    score=3,
    qualified=True,
)


def offered() -> HandoverRequest:
    return HandoverRequest(id="hr-0001", session_id="session-0001", lead=QUALIFIED_LEAD)


def accepted_in(mode: HandoverMode) -> HandoverRequest:
    """An offer the Visitor took, in the mode Availability and the flag decided."""
    return transition(transition(offered(), "accepted_by_user"), "pending_strategist", mode)


def test_the_states_are_the_ones_the_spec_names() -> None:
    """The eight states of ADR-0007. A state added here without a transition would be a state
    a request could never leave; one removed would be a request the Console cannot label."""
    assert HANDOVER_STATES == (
        "offered",
        "accepted_by_user",
        "pending_strategist",
        "strategist_joined",
        "in_call",
        "ended",
        "declined",
        "no_strategist_available",
    )


@pytest.mark.parametrize("start", HANDOVER_STATES)
@pytest.mark.parametrize("target", HANDOVER_STATES)
def test_every_pair_of_states_is_allowed_exactly_when_the_spec_allows_it(
    start: str, target: str
) -> None:
    """The whole 8x8 grid: 7 transitions are legal and the other 57 are not — including every
    self-transition, so a repeated click cannot re-enter the state a request is already in."""
    assert may_transition(start, target) is ((start, target) in ALLOWED)


def test_accepting_an_offer_moves_the_request_to_accepted_by_user() -> None:
    accepted = transition(offered(), "accepted_by_user")

    assert accepted.state == "accepted_by_user"
    # Everything else is carried, not rebuilt: the Lead snapshot is what the Strategist reads.
    assert accepted.id == "hr-0001"
    assert accepted.session_id == "session-0001"
    assert accepted.lead == QUALIFIED_LEAD


def test_the_mode_is_recorded_on_the_transition_that_decides_it() -> None:
    """Mode is decided at acceptance and nowhere else: `video` when a Strategist is online and
    the flag is on, `callback` otherwise (ADR-0007)."""
    pending = accepted_in("callback")

    assert pending.state == "pending_strategist"
    assert pending.mode == "callback"


def test_a_transition_that_names_no_mode_keeps_the_one_the_request_already_has() -> None:
    """A Callback that later runs out of Strategists is still a Callback."""
    pending = accepted_in("callback")

    gave_up = transition(pending, "no_strategist_available")

    assert gave_up.mode == "callback"


def test_declining_an_offer_ends_the_request_without_a_mode() -> None:
    """A declined offer never became a Hand-over, so it has no mode to show in the Console."""
    declined = transition(offered(), "declined")

    assert declined.state == "declined"
    assert declined.mode is None


def test_a_transition_the_machine_does_not_allow_is_refused_by_name() -> None:
    """The Visitor's browser, the Console and a retried request all reach the same endpoints,
    so the refusal has to name both states — a 409 that says only "invalid" is a bug report
    nobody can act on."""
    with pytest.raises(InvalidTransitionError) as refused:
        transition(offered(), "in_call")

    assert "offered" in str(refused.value)
    assert "in_call" in str(refused.value)


def test_a_request_that_has_ended_cannot_be_moved_again() -> None:
    """`ended`, `declined` and `no_strategist_available` are terminal: a second click on a
    stale Console tab must not reopen a conversation that is over."""
    ended = transition(
        transition(transition(accepted_in("video"), "strategist_joined"), "in_call"), "ended"
    )

    for target in HANDOVER_STATES:
        with pytest.raises(InvalidTransitionError):
            transition(ended, target)


def test_a_transition_leaves_the_request_it_was_given_untouched() -> None:
    """The request is a value, not a mutable row: the endpoint validates a transition before
    it writes, and a validation that mutated its input would write the new state even when the
    store call afterwards failed."""
    before = offered()

    transition(before, "declined")

    assert before.state == "offered"


def test_a_new_request_id_is_unguessable_and_url_safe() -> None:
    """The id is in a URL the Visitor's browser posts to, and holding it is what proves the
    Session owns the request — so it is minted like the Session id, not counted up."""
    ids = {new_request_id() for _ in range(50)}

    assert len(ids) == 50
    for request_id in ids:
        assert len(request_id) >= 16
        assert request_id.replace("-", "").replace("_", "").isalnum()


def test_a_lead_snapshot_records_what_the_strategist_reads_at_the_moment_of_the_offer() -> None:
    """The snapshot travels on the request so the Console's queue card is one read, not a join
    across two collections for every row. Contact Details are copied raw and deliberately
    (ADR-0006): a tokenised email is a Callback no Strategist can return."""
    snapshot = lead_snapshot(
        Lead(
            session_id="session-0001",
            name="Jane Doe",
            email="jane@example.com",
            company="Acme Manufacturing",
            phone="+1 555 0100",
            role="VP of Operations",
            signals={"industry_fit": "Manufacturing & Logistics"},
            score=3,
            qualified=True,
        )
    )

    assert snapshot == LeadSnapshot(
        name="Jane Doe",
        email="jane@example.com",
        company="Acme Manufacturing",
        phone="+1 555 0100",
        role="VP of Operations",
        signals={"industry_fit": "Manufacturing & Logistics"},
        score=3,
        qualified=True,
    )


# ------------------------------------------------------ the join timeout and the room name


def pending_video_since(moment: datetime) -> HandoverRequest:
    """A video Hand-over the Visitor accepted at `moment`, waiting for a Strategist."""
    return replace(accepted_in("video"), created_at=moment, updated_at=moment)


def test_a_video_hand_over_nobody_joined_within_the_window_has_waited_too_long() -> None:
    """The Visitor is looking at a spinner. Past the window the honest answer is a Callback
    with the Lead already captured, not a room nobody is ever going to enter (ADR-0007)."""
    accepted = datetime(2026, 8, 31, 9, 41, tzinfo=UTC)

    timed_out = join_timed_out(
        pending_video_since(accepted), accepted + timedelta(seconds=121), timeout_seconds=120
    )

    assert timed_out is True


def test_a_video_hand_over_still_inside_the_window_is_left_alone() -> None:
    """A Strategist reading the request before they claim it is the normal case, so the
    window has to be a window and not a race with the Console's first paint."""
    accepted = datetime(2026, 8, 31, 9, 41, tzinfo=UTC)

    timed_out = join_timed_out(
        pending_video_since(accepted), accepted + timedelta(seconds=119), timeout_seconds=120
    )

    assert timed_out is False


def test_a_callback_hand_over_never_times_out() -> None:
    """A Callback is already the fallback. Timing it out would move a request a Strategist
    still owes a call to into a terminal state, hours after the Visitor closed the tab."""
    accepted = datetime(2026, 8, 31, 9, 41, tzinfo=UTC)
    waiting = replace(accepted_in("callback"), created_at=accepted, updated_at=accepted)

    assert join_timed_out(waiting, accepted + timedelta(days=1), timeout_seconds=120) is False


@pytest.mark.parametrize("state", ["strategist_joined", "in_call", "ended", "offered"])
def test_only_a_request_still_waiting_for_a_strategist_can_time_out(state: HandoverState) -> None:
    """A Strategist who joined at minute three is in the call, not late for it."""
    accepted = datetime(2026, 8, 31, 9, 41, tzinfo=UTC)
    moved = replace(pending_video_since(accepted), state=state)

    assert join_timed_out(moved, accepted + timedelta(seconds=600), timeout_seconds=120) is False


def test_a_request_with_no_timestamp_is_never_timed_out() -> None:
    """Nothing to measure from is not evidence that nobody came: a request the store has not
    stamped yet is left where it is rather than closed on a guess."""
    now = datetime(2026, 8, 31, 9, 41, tzinfo=UTC)

    assert join_timed_out(accepted_in("video"), now, timeout_seconds=120) is False


def test_a_timestamp_without_a_timezone_is_read_as_utc() -> None:
    """Everything this service writes is UTC. A store that hands back a naive datetime must
    not make the comparison raise in the middle of a Visitor's status poll."""
    accepted = datetime(2026, 8, 31, 9, 41)
    waiting = replace(accepted_in("video"), created_at=accepted, updated_at=accepted)

    assert join_timed_out(waiting, datetime(2026, 8, 31, 9, 45, tzinfo=UTC), 120) is True


def test_a_room_name_is_the_request_id_in_a_form_a_daily_url_can_carry() -> None:
    """The design draws the room as `daily.co/cadre-{id}` (docs/design §3.1), so the name is
    the request id and not a second identifier a Strategist would have to look up."""
    assert room_name("Ab3-_x9") == "cadre-ab3-_x9"


def test_a_room_name_holds_nothing_a_url_would_have_to_escape() -> None:
    """The room URL is handed to an iframe and read aloud from the Console's banner."""
    assert room_name("hr/0001 é.9") == "cadre-hr-0001---9"


def test_two_handover_requests_never_share_a_room() -> None:
    """A shared room is two Visitors in one call. The names come from ids minted with 144
    bits of randomness, so they differ for the same reason the ids do."""
    names = {room_name(new_request_id()) for _ in range(200)}

    assert len(names) == 200
