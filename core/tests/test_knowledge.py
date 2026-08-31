"""The Knowledge Base compiler — seam S2."""

from core.adapters.knowledge_files import FileKnowledgeSource
from core.adapters.stub_demo_script import demo_fallback, demo_scripts
from core.citations import CITATION_PATTERN
from core.knowledge import (
    KNOWLEDGE_TOKEN_BUDGET,
    compile_knowledge_base,
    compile_topic,
    estimate_tokens,
    render_knowledge_block,
)
from core.provider import TextDelta, ToolCall
from core.tools.escalate import ESCALATION_COPY

SERVICES = """\
# Services

## What Cadre does

Cadre AI is a consultancy focused on using AI to drive revenue growth.

Many companies get less efficient as they scale.

## AI Strategy & Facilitation

The 45-day AI Transformation Intensive.
"""

INDUSTRIES = """\
# Industries

## Industries Cadre serves

Professional Services, Private Equity, Real Estate.
"""


def test_every_heading_becomes_a_kb_section_addressed_by_topic_and_slug() -> None:
    sections = compile_topic("services", SERVICES)

    assert [section.id for section in sections] == [
        "services#services",
        "services#what-cadre-does",
        "services#ai-strategy-facilitation",
    ]


def test_a_kb_section_carries_the_prose_under_its_heading() -> None:
    _title, what_cadre_does, _strategy = compile_topic("services", SERVICES)

    assert what_cadre_does.heading == "What Cadre does"
    assert what_cadre_does.body == (
        "Cadre AI is a consultancy focused on using AI to drive revenue growth.\n\n"
        "Many companies get less efficient as they scale."
    )


def test_two_headings_with_the_same_words_stay_separately_addressable() -> None:
    """Citations are only useful if one id names exactly one KB Section."""
    sections = compile_topic("contact", "## Contact\n\nfirst\n\n## Contact\n\nsecond\n")

    assert [section.id for section in sections] == ["contact#contact", "contact#contact-2"]
    assert [section.body for section in sections] == ["first", "second"]


def test_the_compiled_knowledge_base_orders_topics_the_same_way_every_time() -> None:
    """The cached prompt prefix has to be byte-stable, so the order cannot follow a dict or
    a directory listing (ADR-0001)."""
    forwards = compile_knowledge_base({"services": SERVICES, "industries": INDUSTRIES})
    backwards = compile_knowledge_base({"industries": INDUSTRIES, "services": SERVICES})

    assert forwards == backwards
    assert [section.topic for section in forwards] == ["industries"] * 2 + ["services"] * 3


def test_the_rendered_block_labels_every_section_with_the_id_the_assistant_must_cite() -> None:
    block = render_knowledge_block(compile_topic("industries", INDUSTRIES))

    assert "[industries#industries-cadre-serves] Industries Cadre serves" in block
    assert "Professional Services, Private Equity, Real Estate." in block


def test_the_authored_topics_compile_to_the_ids_the_assistant_cites() -> None:
    sections = compile_knowledge_base(FileKnowledgeSource().documents())

    ids = {section.id for section in sections}
    assert {"services#what-cadre-does", "industries#industries-cadre-serves"} <= ids
    assert all(section.body for section in sections if section.level > 1)


def demo_script_texts() -> list[str]:
    """Every claim the demo script makes, as one string per claim: a streamed answer with its
    deltas joined back up (they are chunked mid-sentence, so a figure and its marker can arrive
    separately), and each tool argument on its own."""
    texts: list[str] = []
    for script in [*demo_scripts().values(), demo_fallback()]:
        for response in script:
            deltas = [event.text for event in response if isinstance(event, TextDelta)]
            if deltas:
                texts.append("".join(deltas))
            for event in response:
                if isinstance(event, ToolCall):
                    texts.extend(str(argument) for argument in event.arguments.values())
    return texts


# A figure the demo script quotes, and the one KB Section that actually carries it. Citing the
# topic's summary section instead is the failure this guards: the chip looks right, and the
# section it opens does not contain the number the Visitor was just given.
FIGURES_AND_THE_SECTIONS_THAT_CARRY_THEM = (
    ("50+ companies", "services#why-companies-bring-in-an-ai-partner"),
    ("eight leaders", "not-published#company-size-founding-and-funding"),
    ("220 hours a month", "case-studies#supplier-automation-manufacturing-logistics"),
    ("$420,000", "case-studies#ai-powered-housing-visibility-system-hospitality"),
)


def test_every_id_the_demo_script_cites_resolves_to_a_kb_section() -> None:
    """`make dev` renders a citation chip for every marker the demo script writes. A renamed
    heading has to fail here rather than ship a chip that points at nothing."""
    ids = {section.id for section in compile_knowledge_base(FileKnowledgeSource().documents())}

    cited: set[str] = set()
    for text in demo_script_texts():
        cited |= set(CITATION_PATTERN.findall(text))

    assert cited, "the demo script cites nothing, so this guard proves nothing"
    assert cited <= ids


def test_every_figure_the_demo_script_quotes_cites_the_section_that_carries_it() -> None:
    """A resolvable id is not the same as a supporting one. Where the demo script states a
    published figure, the marker beside it has to name the KB Section that holds that figure."""
    bodies = {
        section.id: section.body
        for section in compile_knowledge_base(FileKnowledgeSource().documents())
    }

    for figure, section_id in FIGURES_AND_THE_SECTIONS_THAT_CARRY_THEM:
        assert figure in bodies[section_id], f"{section_id} no longer carries {figure!r}"

    for text in demo_script_texts():
        for figure, section_id in FIGURES_AND_THE_SECTIONS_THAT_CARRY_THEM:
            if figure in text:
                assert section_id in CITATION_PATTERN.findall(text), (
                    f"the demo script states {figure!r} without citing {section_id}: {text}"
                )


def test_the_knowledge_base_covers_every_topic_the_brief_asks_about() -> None:
    """The brief's scenarios are the coverage bar: what Cadre does, industries, booking a
    call, the Portal, the AI Maturity Index, LLM selection and data security — plus the
    topic that exists so the Assistant can escalate instead of inventing."""
    sections = compile_knowledge_base(FileKnowledgeSource().documents())

    assert {section.topic for section in sections} == {
        "case-studies",
        "contact",
        "data-security",
        "industries",
        "maturity-index",
        "not-published",
        "partners-and-models",
        "portal",
        "services",
    }


def test_every_kb_section_id_is_unique_across_the_whole_knowledge_base() -> None:
    """A citation is only worth rendering if one id names exactly one KB Section."""
    ids = [section.id for section in compile_knowledge_base(FileKnowledgeSource().documents())]

    assert len(ids) == len(set(ids))


def test_what_cadre_does_not_publish_is_itself_a_citable_topic() -> None:
    """Escalating honestly means citing the section that says the fact is not published, so
    every Trap Question the prompt lists needs a KB Section of its own."""
    sections = compile_knowledge_base(FileKnowledgeSource().documents())

    not_published = {section.id for section in sections if section.topic == "not-published"}
    assert {
        "not-published#pricing",
        "not-published#portal-login",
        "not-published#security-certifications-and-data-agreements",
        "not-published#company-size-founding-and-funding",
        "not-published#named-availability-and-start-dates",
        "not-published#comparisons-with-other-firms",
        "not-published#outcome-guarantees",
        "not-published#anything-not-listed-here",
    } <= not_published


def test_the_token_estimate_rounds_against_the_budget_rather_than_towards_it() -> None:
    """No tokeniser is installed and none is wanted for a guard rail: 3.5 characters per token
    is below what English prose actually costs, so the estimate reads high and the budget bites
    before the provider does."""
    assert estimate_tokens("") == 0
    assert estimate_tokens("x" * 350) == 100
    assert estimate_tokens("x" * 351) == 101


def test_the_compiled_knowledge_base_fits_inside_the_cached_prompt_budget() -> None:
    """The whole Knowledge Base sits in the cached prefix of every prompt (ADR-0001), and
    docs/architecture.md prices a Turn on it, so its size is a decision with a number."""
    block = render_knowledge_block(compile_knowledge_base(FileKnowledgeSource().documents()))

    assert estimate_tokens(block) < KNOWLEDGE_TOKEN_BUDGET


def test_every_id_the_escalation_copy_cites_resolves_to_a_kb_section() -> None:
    """The per-reason Escalation copy cites the KB Section that records the absence it is
    refusing on. A renamed heading has to fail here rather than ship an Escalation whose
    citation chip points at nothing."""
    ids = {section.id for section in compile_knowledge_base(FileKnowledgeSource().documents())}

    cited: set[str] = set()
    for languages in ESCALATION_COPY.values():
        for copy in languages.values():
            cited |= set(CITATION_PATTERN.findall(copy.body))

    assert cited, "the Escalation copy cites nothing, so this guard proves nothing"
    assert cited <= ids
