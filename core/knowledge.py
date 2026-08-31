"""Compile the Knowledge Base's markdown topics into citable KB Sections (ADR-0001).

The Assistant may state only what a KB Section states, and must cite the section it came
from, so every heading in every topic file gets a stable id of the form `topic#heading-slug`.
The compiled block goes into the cached prefix of the system prompt: its order is derived from
the topic name and the document, never from a dict or a directory listing, because a byte
change to the prefix invalidates the prompt cache for every Session.
"""

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_CODE_FENCE = re.compile(r"^\s*(```|~~~)")
_NOT_SLUGGABLE = re.compile(r"[^a-z0-9]+")

# What the compiled block may cost in the cached prompt prefix. docs/architecture.md
# prices a Turn on a 25K-token system prompt, and the Knowledge Base is nearly all of it,
# so the number is a budget the authored topics are held to rather than an observation.
KNOWLEDGE_TOKEN_BUDGET = 25_000

# English prose runs about four characters per token; three and a half reads high on
# purpose, so the guard trips before the provider's own count does.
CHARACTERS_PER_TOKEN = 3.5


@dataclass(frozen=True)
class KBSection:
    """The smallest citable unit of the Knowledge Base."""

    id: str
    topic: str
    heading: str
    level: int
    body: str


class KnowledgeSource(Protocol):
    """Where the Knowledge Base's topics come from (markdown files today, Firestore later)."""

    @property
    def location(self) -> str:
        """Where this source looked — a directory, later a collection. For failure messages
        and startup logs: "the Knowledge Base is empty" is only actionable with a path."""
        ...

    def documents(self) -> Mapping[str, str]:
        """Topic name (the citation's left-hand side) to that topic's markdown."""
        ...


def estimate_tokens(text: str) -> int:
    """A tokeniser-free size estimate, rounded up. Exact enough for a budget that exists
    to catch a Knowledge Base that has doubled, not to bill anyone."""
    return math.ceil(len(text) / CHARACTERS_PER_TOKEN)


def slugify(heading: str) -> str:
    """The right-hand side of a citation: kebab-case, ASCII, stable across edits of the prose."""
    return _NOT_SLUGGABLE.sub("-", heading.casefold()).strip("-")


def compile_topic(topic: str, markdown: str) -> tuple[KBSection, ...]:
    """One KB Section per heading, in document order. Prose before the first heading is not
    addressable and is therefore dropped — a fact nothing can cite is a fact the Assistant
    may not state."""
    sections: list[KBSection] = []
    slugs_used: dict[str, int] = {}
    heading: str | None = None
    level = 0
    body: list[str] = []
    in_code_fence = False

    def close() -> None:
        if heading is None:
            return
        slug = slugify(heading)
        seen = slugs_used.get(slug, 0) + 1
        slugs_used[slug] = seen
        # A repeated heading still needs one id per section, or a citation is ambiguous.
        suffix = "" if seen == 1 else f"-{seen}"
        sections.append(
            KBSection(
                id=f"{topic}#{slug}{suffix}",
                topic=topic,
                heading=heading,
                level=level,
                body="\n".join(body).strip(),
            )
        )

    for line in markdown.splitlines():
        if _CODE_FENCE.match(line):
            in_code_fence = not in_code_fence
        match = None if in_code_fence else _HEADING.match(line)
        if match is None:
            body.append(line)
            continue
        close()
        heading = match.group(2)
        level = len(match.group(1))
        body = []
    close()
    return tuple(sections)


def compile_knowledge_base(documents: Mapping[str, str]) -> tuple[KBSection, ...]:
    """Every topic's KB Sections, in an order that does not depend on how they were loaded."""
    return tuple(
        section for topic in sorted(documents) for section in compile_topic(topic, documents[topic])
    )


def render_knowledge_block(sections: Sequence[KBSection]) -> str:
    """The Knowledge Base as the model reads it: every section labelled with the id to cite."""
    return "\n\n".join(
        f"[{section.id}] {section.heading}" + (f"\n{section.body}" if section.body else "")
        for section in sections
    )
