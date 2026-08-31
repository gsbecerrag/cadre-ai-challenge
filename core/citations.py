"""Find the `[topic#heading]` markers the Assistant writes into its answers.

The marker is the contract between the system prompt's grounding rule and the chat widget's
citation chips; the server needs the same reading of it to attach citations to an Escalation.
"""

import re

CITATION_PATTERN = re.compile(r"\[([a-z0-9][a-z0-9-]*#[a-z0-9][a-z0-9-]*)\]")


def find_citations(text: str) -> tuple[str, ...]:
    """The KB Section ids cited in the text, first mention first, each one once."""
    return tuple(dict.fromkeys(CITATION_PATTERN.findall(text)))
