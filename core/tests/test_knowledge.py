"""The Knowledge Base compiler — seam S2."""

from core.adapters.knowledge_files import FileKnowledgeSource
from core.knowledge import compile_knowledge_base, compile_topic, render_knowledge_block

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
