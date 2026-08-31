"""The `KnowledgeSource` that reads the Knowledge Base from `knowledge/*.md` (ADR-0001).

The topic name a citation uses is the file stem, so renaming a file changes every id in it.
"""

from collections.abc import Mapping
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_DIR = REPO_ROOT / "knowledge"

# Prose for humans working on the Knowledge Base, not facts the Assistant may state.
EXCLUDED_STEMS = frozenset({"README"})


class FileKnowledgeSource:
    """Markdown topics on disk, read once at process start."""

    def __init__(self, directory: Path = KNOWLEDGE_DIR) -> None:
        self._directory = directory

    @property
    def location(self) -> str:
        return str(self._directory)

    def documents(self) -> Mapping[str, str]:
        return {
            path.stem: path.read_text(encoding="utf-8")
            for path in sorted(self._directory.glob("*.md"))
            if path.stem not in EXCLUDED_STEMS
        }
