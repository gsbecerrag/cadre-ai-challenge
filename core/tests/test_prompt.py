"""System prompt assembly — seam S2."""

from datetime import date

from core.prompt import build_system_prompt

KNOWLEDGE_BLOCK = "[services#what-cadre-does] What Cadre does\nCadre AI is a consultancy."


def test_the_prompt_is_assembled_in_the_order_the_spec_fixes() -> None:
    """The order is a decision, not a detail: the cached prefix only stays warm while the
    blocks before the volatile tail keep their bytes (ADR-0001)."""
    prompt = build_system_prompt(KNOWLEDGE_BLOCK, today=date(2026, 8, 30))

    assert [name for name, _ in prompt.cached_sections] == [
        "identity",
        "knowledge_base",
        "grounding",
        "escalation",
        "personal_data",
        "qualification",
        "style",
        "tools",
    ]


def test_the_knowledge_base_block_comes_before_any_volatile_content() -> None:
    prompt = build_system_prompt(KNOWLEDGE_BLOCK, today=date(2026, 8, 30))

    assert KNOWLEDGE_BLOCK in prompt.cached
    assert "2026-08-30" in prompt.volatile
    assert prompt.text.index(KNOWLEDGE_BLOCK) < prompt.text.index("2026-08-30")


def test_the_cached_prefix_does_not_move_when_only_the_volatile_tail_changes() -> None:
    monday = build_system_prompt(KNOWLEDGE_BLOCK, today=date(2026, 8, 30))
    tuesday = build_system_prompt(KNOWLEDGE_BLOCK, today=date(2026, 8, 31))

    assert monday.cached == tuesday.cached
    assert monday.volatile != tuesday.volatile


def test_the_prompt_names_the_citation_marker_the_web_app_parses() -> None:
    """The chat renders a citation chip for every `[topic#heading]` marker in the answer, so
    the marker syntax is a contract between the prompt and the widget, not house style."""
    prompt = build_system_prompt(KNOWLEDGE_BLOCK, today=date(2026, 8, 30))

    assert "[topic#heading]" in prompt.cached
