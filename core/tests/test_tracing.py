"""What a Turn is tagged with — seam S2, a pure function over what the Turn did.

Tags are the vocabulary a Cadre engineer filters a week of conversations by, so they are worth
pinning away from a running Turn: the same Turn always produces the same tags, in the same
order, whatever order the tools happened to run in.
"""

from core.tracing import PROVIDER_ERROR_TAG, TOOL_TAGS, turn_tags


def test_a_turn_that_ran_no_tools_and_redacted_nothing_carries_no_tags() -> None:
    assert turn_tags([]) == ()


def test_each_tool_the_turn_ran_names_what_the_turn_did() -> None:
    """`escalate` is a refusal, `capture_lead` is a Lead, `show_walkthrough` is a card — the
    three things worth finding a week of conversations by."""
    assert turn_tags(["escalate"]) == ("escalated",)
    assert turn_tags(["capture_lead"]) == ("lead_captured",)
    assert turn_tags(["show_walkthrough"]) == ("walkthrough_shown",)


def test_the_tags_do_not_depend_on_the_order_the_tools_ran_in() -> None:
    """Two Turns that did the same things read the same in Langfuse; a tag list that followed
    the model's whim would make "escalated, lead_captured" and its reverse look like two
    different kinds of Turn."""
    assert turn_tags(["capture_lead", "escalate"]) == turn_tags(["escalate", "capture_lead"])


def test_a_tool_called_twice_in_one_turn_is_still_one_tag() -> None:
    assert turn_tags(["capture_lead", "capture_lead"]) == ("lead_captured",)


def test_a_tool_name_the_registry_does_not_know_earns_no_tag() -> None:
    """A model can ask for any tool name it likes. An invented one is not a new tag in
    Langfuse — it comes back to the model as a result it can correct (ADR-0004)."""
    assert turn_tags(["teleport_the_visitor"]) == ()


def test_the_language_an_escalation_answered_in_is_a_tag() -> None:
    """Known for free, because the Escalation copy is looked up per language — and "how many
    Spanish Turns end in a refusal" is then a filter rather than a research project."""
    assert turn_tags(["escalate"], "es") == ("escalated", "language:es")
    assert turn_tags(["escalate"], None) == ("escalated",)


def test_a_turn_that_failed_at_the_provider_says_so() -> None:
    assert PROVIDER_ERROR_TAG in turn_tags([], provider_error=True)


def test_the_redaction_manifest_becomes_one_tag_per_category_and_never_a_value() -> None:
    """Counts stay in metadata; the categories are tags, so "how often does a Visitor paste a
    card" is a filter over Traces (ADR-0006)."""
    tags = turn_tags([], redactions={"card": 2, "ssn": 1})

    assert tags == ("redacted:card", "redacted:ssn")
    assert not any("2" in tag for tag in tags)


def test_every_tool_the_assistant_can_call_has_a_tag_waiting_for_it() -> None:
    """Ticket 11's `offer_live_handover` is in the table already: a Hand-over offer becomes a
    tag the day the tool is registered, with no change here or in the Turn."""
    assert TOOL_TAGS["offer_live_handover"] == "handover_offered"
