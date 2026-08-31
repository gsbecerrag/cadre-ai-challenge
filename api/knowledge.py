"""`GET /api/knowledge/sections` — the title behind every citation chip.

A chip that reads `[not-published#pricing]` is honest and tells the Visitor nothing. The widget
fetches this list once, the first time the panel opens, and shows the heading behind the id.

It is deliberately titles only: the section bodies are the Assistant's to quote from the
prompt, not the browser's to download. Serving the whole Knowledge Base here would make a
second, unversioned copy of it that could drift from the one in the cached prompt.
"""

from collections.abc import Sequence

from fastapi import APIRouter
from pydantic import BaseModel

from core.knowledge import KBSection


class SectionTitle(BaseModel):
    """One KB Section as the citation chips need it: the id to match, and what to show."""

    id: str
    title: str
    topic: str


class SectionTitles(BaseModel):
    sections: list[SectionTitle]


def create_knowledge_router(sections: Sequence[KBSection]) -> APIRouter:
    """The sections are compiled once at startup and passed in, so this endpoint and the
    prompt's cached block can never disagree about what the Knowledge Base contains."""
    titles = SectionTitles(
        sections=[
            SectionTitle(id=section.id, title=section.heading, topic=section.topic)
            for section in sections
        ]
    )
    router = APIRouter(tags=["knowledge"])

    @router.get("/knowledge/sections")
    async def knowledge_sections() -> SectionTitles:
        return titles

    return router
