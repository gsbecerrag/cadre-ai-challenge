"""Walkthrough Cards through the chat endpoint — seam S1, stub provider, in-memory store.

What these pin is the half of the card the model does not write: the link. The Assistant names
a destination id, and either the catalogue resolves it — in which case the Visitor gets a
button that goes somewhere real — or it does not, in which case the model gets the rejection
back and the Visitor's Turn carries on without a card.
"""

from fastapi.testclient import TestClient

from api.tests.conftest import sse_events
from core.adapters.stub_provider import StubModelProvider
from core.provider import TextDelta, ToolCall, Usage
from core.tools.walkthroughs import CONTACT_FORM_URL

SPEND = Usage(input_tokens=12_400, output_tokens=48, cached_tokens=12_200, cost_usd=0.0031)

# The reference flow from the design artboard (docs/design/DESIGN-BRIEF.md §2.5): a short cited
# sentence, then the card.
INTRO = (
    "Here's where that lives — the Portal tracks tools, agents, training, and results "
    "[portal#what-the-portal-tracks]."
)
CLOSING = "Anything else I can look up for you?"

WALKTHROUGH = ToolCall(
    id="call-0800",
    name="show_walkthrough",
    arguments={
        "title": "See your agents' results in the Portal",
        "steps": [
            "Open the Cadre Portal from the link your Cadre contact gave you "
            "[portal#how-to-access-the-portal]",
            "Go to Agents in the left menu",
            "Pick an agent to see its runs, hours saved and status",
        ],
        "destination": "portal.agents",
    },
)


def walkthrough_with(**changes: object) -> ToolCall:
    return ToolCall(
        id=WALKTHROUGH.id, name=WALKTHROUGH.name, arguments={**WALKTHROUGH.arguments, **changes}
    )


def card_payload(response: object) -> dict[str, object]:
    cards = [data for name, data in sse_events(response) if name == "card"]  # type: ignore[arg-type]
    assert len(cards) == 1
    return cards[0]


def test_a_walkthrough_streams_a_card_with_the_link_its_destination_resolves_to(
    client: TestClient, provider: StubModelProvider
) -> None:
    """The Assistant names `portal.agents`; the Visitor gets the route and the anchor of the
    demo Portal page that actually shows an agent's results, and the markers in the steps
    become citation chips rather than staying in the text."""
    provider.script("agents' results", [TextDelta(INTRO), WALKTHROUGH], [TextDelta(CLOSING), SPEND])

    response = client.post("/api/chat", json={"message": "How do I see my agents' results?"})

    assert [name for name, _ in sse_events(response)] == [
        "text",
        "tool",
        "card",
        "tool",
        "text",
        "done",
    ]
    assert card_payload(response) == {
        "title": "See your agents' results in the Portal",
        "steps": [
            "Open the Cadre Portal from the link your Cadre contact gave you",
            "Go to Agents in the left menu",
            "Pick an agent to see its runs, hours saved and status",
        ],
        "destination": {
            "id": "portal.agents",
            "label": "Open demo Portal",
            "href": "/portal/agents#portal-agents-results",
            "external": False,
        },
        "citations": ["portal#how-to-access-the-portal"],
    }


def test_getting_scored_on_the_maturity_index_walks_to_the_published_contact_form(
    client: TestClient, provider: StubModelProvider
) -> None:
    """There is no self-serve scoring page, so the card opens the contact form in a new tab —
    the one destination for a process that starts with a Strategist."""
    scored = walkthrough_with(
        title="Get scored on the AI Maturity Index",
        steps=[
            "Tell Cadre about your company through the contact form",
            "A strategist scores you across the eight-pillar framework "
            "[maturity-index#how-to-get-scored]",
        ],
        destination="maturity.get-scored",
    )
    provider.script("maturity index", [scored], [TextDelta(CLOSING), SPEND])

    response = client.post("/api/chat", json={"message": "How do I get scored on the Maturity Index?"})

    assert card_payload(response)["destination"] == {
        "id": "maturity.get-scored",
        "label": "Open the contact form",
        "href": CONTACT_FORM_URL,
        "external": True,
    }


def test_a_destination_the_assistant_invents_never_reaches_the_visitor(
    client: TestClient, provider: StubModelProvider
) -> None:
    """A model can put anything in the id. Nothing outside the catalogue becomes a link: the
    Turn ends normally and the model reads back which destinations exist."""
    provider.script(
        "billing", [walkthrough_with(destination="portal.billing")], [TextDelta(CLOSING), SPEND]
    )

    response = client.post("/api/chat", json={"message": "Where is my billing page?"})

    assert [name for name, _ in sse_events(response)] == ["tool", "tool", "text", "done"]
    rejection = provider.requests[1].messages[-1]
    assert rejection.role == "tool"
    assert "no walkthrough destination 'portal.billing'" in rejection.content
    assert "portal.agents" in rejection.content


def test_a_walkthrough_the_visitor_cannot_follow_is_sent_back_to_the_assistant(
    client: TestClient, provider: StubModelProvider
) -> None:
    """A card is two to four steps. One step is a sentence, and nine is a manual; either way
    the model gets a result it can correct instead of the Visitor getting the card."""
    provider.script(
        "one step", [walkthrough_with(steps=["Open the Portal"])], [TextDelta(CLOSING), SPEND]
    )

    response = client.post("/api/chat", json={"message": "one step please"})

    names = [name for name, _ in sse_events(response)]
    assert "card" not in names
    assert names == ["tool", "tool", "text", "done"]
    assert "2 to 4 steps" in provider.requests[1].messages[-1].content


def test_an_escalation_names_the_language_the_visitor_is_reading_it_in(
    client: TestClient, provider: StubModelProvider
) -> None:
    """The Escalation card's own chrome — its "Next step:" label — has to follow the language
    of the card, not the widget's toggle, or a Spanish refusal gets an English label."""
    spanish = ToolCall(
        id="call-0801",
        name="escalate",
        arguments={
            "reason": "pricing",
            "known": "",
            "next_step": "Escribe a hello@gocadre.ai.",
            "language": "es",
        },
    )
    provider.script("cuesta", [spanish], [TextDelta("¿Algo más?"), SPEND])

    response = client.post("/api/chat", json={"message": "¿Cuánto cuesta?"})

    escalations = [data for name, data in sse_events(response) if name == "escalation"]
    assert escalations[0]["language"] == "es"
