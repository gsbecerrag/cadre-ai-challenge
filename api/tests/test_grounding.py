"""Grounding and honest Escalation — seam S1, with the stub provider and in-memory store.

A Trap Question is a question that sounds answerable and is not in the Knowledge Base. What
these tests pin is that the Visitor sees Cadre's own published wording for the refusal, in
their language, with a concrete next step — and never a fact the Assistant made up on the way.
"""

from fastapi.testclient import TestClient

from api.tests.conftest import sse_events
from core.adapters.knowledge_files import FileKnowledgeSource
from core.adapters.stub_provider import StubModelProvider
from core.knowledge import compile_knowledge_base
from core.provider import TextDelta, ToolCall, Usage
from core.tools.escalate import ESCALATION_COPY

SPEND = Usage(input_tokens=12_400, output_tokens=48, cached_tokens=12_200, cost_usd=0.0031)

KNOWN = (
    "The engagement behind that question is the 45-day AI Transformation Intensive "
    "[services#the-ai-transformation-intensive]."
)
NEXT_STEP = "Write to hello@gocadre.ai for a scoped quote [contact#how-to-reach-cadre]."


def pricing_escalation(language: str, known: str = KNOWN) -> ToolCall:
    return ToolCall(
        id="call-0400",
        name="escalate",
        arguments={
            "reason": "pricing",
            "known": known,
            "next_step": NEXT_STEP,
            "language": language,
        },
    )


def escalation_payload(response: object) -> dict[str, object]:
    escalations = [data for name, data in sse_events(response) if name == "escalation"]  # type: ignore[arg-type]
    assert len(escalations) == 1
    return escalations[0]


def test_a_pricing_trap_question_escalates_in_cadres_own_published_wording(
    client: TestClient, provider: StubModelProvider
) -> None:
    """The Assistant never writes the title of an Escalation. Per-reason copy does, so the
    refusal reads the same every time and cannot drift into a quote."""
    provider.script(
        "what does it cost", [pricing_escalation("en")], [TextDelta("Anything else?"), SPEND]
    )

    response = client.post("/api/chat", json={"message": "What does it cost?"})

    card = escalation_payload(response)
    assert card["title"] == "Cadre doesn't publish pricing"
    assert card["body"] == (
        "I can't quote a price for Strategy, Facilitation, Engineering, or Agents "
        "engagements — Cadre doesn't publish them. The only published price is the PE AI "
        "Value Creation Playbook at $5,000 per firm. The engagement behind that question is "
        "the 45-day AI Transformation Intensive."
    )
    assert card["next_step"] == "Write to hello@gocadre.ai for a scoped quote."


def test_an_escalation_cites_only_kb_sections_that_exist(
    client: TestClient, provider: StubModelProvider
) -> None:
    """A chip that points at nothing is an invented fact with a citation stapled to it."""
    provider.script(
        "what does it cost", [pricing_escalation("en")], [TextDelta("Anything else?"), SPEND]
    )

    response = client.post("/api/chat", json={"message": "What does it cost?"})

    ids = {section.id for section in compile_knowledge_base(FileKnowledgeSource().documents())}
    citations = escalation_payload(response)["citations"]
    assert citations == [
        "not-published#pricing",
        "services#the-ai-transformation-intensive",
        "contact#how-to-reach-cadre",
    ]
    assert set(citations) <= ids


def test_a_spanish_visitor_reads_the_escalation_in_spanish(
    client: TestClient, provider: StubModelProvider
) -> None:
    provider.script(
        "cuánto cuesta", [pricing_escalation("es", known="")], [TextDelta("¿Algo más?"), SPEND]
    )

    response = client.post("/api/chat", json={"message": "¿Cuánto cuesta el Intensivo?"})

    card = escalation_payload(response)
    assert card["title"] == "Cadre no publica precios"
    assert card["body"] == ESCALATION_COPY["pricing"]["es"].body.replace(
        " [not-published#pricing]", ""
    )


def test_an_escalation_reason_the_assistant_invents_still_reads_honestly(
    client: TestClient, provider: StubModelProvider
) -> None:
    """The reason is an enum the model fills in, and a model can put anything there. An
    unknown reason falls back to the honest generic copy rather than ending the Turn."""
    invented = ToolCall(
        id="call-0401",
        name="escalate",
        arguments={
            "reason": "how_many_llamas",
            "known": "",
            "next_step": "Ask the team at hello@gocadre.ai.",
            "language": "en",
        },
    )
    provider.script("llamas", [invented], [TextDelta("Anything else?"), SPEND])

    response = client.post("/api/chat", json={"message": "How many llamas?"})

    card = escalation_payload(response)
    assert card["title"] == "I don't have that information"
    assert card["next_step"] == "Ask the team at hello@gocadre.ai."


def test_an_escalation_without_a_next_step_is_sent_back_to_the_assistant(
    client: TestClient, provider: StubModelProvider
) -> None:
    """An Escalation with nothing for the Visitor to do is worse than no Escalation, so the
    tool rejects it and the model gets a result it can correct."""
    empty = ToolCall(
        id="call-0402",
        name="escalate",
        arguments={"reason": "pricing", "known": "", "next_step": " ", "language": "en"},
    )
    provider.script("no next step", [empty], [TextDelta("Anything else?"), SPEND])

    response = client.post("/api/chat", json={"message": "no next step please"})

    names = [name for name, _ in sse_events(response)]
    assert "escalation" not in names
    assert names == ["tool", "tool", "text", "done"]
