"""Read the `[topic#heading]` markers the Assistant writes into its answers.

The marker is the contract between the system prompt's grounding rule and the chat widget's
citation chips. A marker that has become a chip must not also be left sitting in the prose, so
lifting it out and cleaning up after it are one operation.
"""

import re

CITATION_PATTERN = re.compile(r"\[([a-z0-9][a-z0-9-]*#[a-z0-9][a-z0-9-]*)\]")
_REPEATED_SPACES = re.compile(r"[ \t]{2,}")
_SPACE_BEFORE_PUNCTUATION = re.compile(r" +([.,;:!?)])")


def split_citations(text: str) -> tuple[str, tuple[str, ...]]:
    """The text without its markers, and the KB Section ids they named — first mention first,
    each one once."""
    citations = tuple(dict.fromkeys(CITATION_PATTERN.findall(text)))
    without_markers = CITATION_PATTERN.sub("", text)
    tidied = _SPACE_BEFORE_PUNCTUATION.sub(
        r"\1", _REPEATED_SPACES.sub(" ", without_markers)
    ).strip()
    return tidied, citations
