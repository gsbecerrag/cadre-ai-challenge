"""The destinations a Walkthrough Card is allowed to send a Visitor to.

The Assistant writes the title and the steps; it does not write the link. It names one id from
this table and the link comes from here, in code. That is the whole safety property of the
tool: the Knowledge Base records that Cadre publishes no Portal address and no self-serve
Maturity Index quiz, so a model free to write its own URL would eventually write one anyway.

Two kinds of destination sit here. A Portal id resolves to a route in this repository's demo
Portal (ticket 07) with the fragment of the stable id the page renders, so the CTA is a
client-side navigation that leaves the chat panel and its transcript mounted. Anything that
starts with a Strategist — getting scored on the AI Maturity Index included — resolves to the
published contact form and opens in a new tab, because there is no page to send them to and
inventing one is the failure this table prevents.
"""

from collections.abc import Mapping

from core.events import CardDestination

# The one URL here Cadre owns rather than this repository; it is published in the `contact` KB
# Section, and a test holds the two together.
CONTACT_FORM_URL = "https://www.cadreai.com/contact"

OPEN_DEMO_PORTAL = "Open demo Portal"
OPEN_CONTACT_FORM = "Open the contact form"


def _portal(destination_id: str, route: str, anchor: str) -> CardDestination:
    return CardDestination(
        id=destination_id,
        label=OPEN_DEMO_PORTAL,
        href=f"{route}#{anchor}",
        external=False,
    )


def _contact(destination_id: str) -> CardDestination:
    return CardDestination(
        id=destination_id,
        label=OPEN_CONTACT_FORM,
        href=CONTACT_FORM_URL,
        external=True,
    )


WALKTHROUGH_DESTINATIONS: Mapping[str, CardDestination] = {
    destination.id: destination
    for destination in (
        _portal("portal.dashboard", "/portal", "portal-nav"),
        _portal("portal.tools", "/portal/tools", "portal-tools-list"),
        _portal("portal.agents", "/portal/agents", "portal-agents-results"),
        _portal("portal.training", "/portal/results", "portal-training-progress"),
        _contact("contact.form"),
        _contact("maturity.get-scored"),
    )
}

DESTINATION_IDS: tuple[str, ...] = tuple(WALKTHROUGH_DESTINATIONS)


def resolve_destination(destination_id: str) -> CardDestination | None:
    """The link for an id, or nothing at all when the Assistant named one that does not exist."""
    return WALKTHROUGH_DESTINATIONS.get(destination_id)
