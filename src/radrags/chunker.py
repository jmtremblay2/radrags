"""Document chunking primitives."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass
class Chunk:
    """A single chunk of text extracted from a document.

    Attributes:
        heading: The section heading this chunk belongs to.
        chunk_type: The kind of chunk (e.g. "prose", "code").
        text: The raw text content of the chunk.
        source: The file path or identifier of the source document.

    Example:
        ```python
        from radrags.chunker import Chunk

        chunk = Chunk(
            heading="WireGuard",
            chunk_type="prose",
            text="WireGuard is a simple, fast VPN tunnel.",
            source="configuration/interfaces/wireguard.rst",
        )
        ```
    """

    heading: str
    chunk_type: str
    text: str
    source: str


class DocumentChunker(ABC):
    """Abstract base class for document chunkers."""

    @abstractmethod
    def chunk(self, text: str, docs_root: Path | None = None) -> list[Chunk]:
        """Split document text into a list of chunks."""


HEADING_LEVELS: dict[str, int] = {
    "#": 1,
    "=": 2,
    "*": 2,
    "-": 3,
    "~": 4,
    "^": 5,
    '"': 6,
}


def _is_adornment_line(line: str) -> bool:
    """Return True if *line* consists of a single repeated character."""
    return bool(line) and len(set(line)) == 1


class RstChunker(DocumentChunker):
    """Chunker for reStructuredText documents."""

    def chunk(self, text: str, docs_root: Path | None = None) -> list[Chunk]:
        """Split RST text into chunks."""
        return []

    def _heading_at(self, lines: Sequence[str], i: int) -> tuple[int, str, int] | None:
        """Detect an RST heading at position *i* in *lines*.

        Returns (level, title, lines_consumed) on match, None otherwise.
        """
        # Form 1: title + underline
        if i + 1 < len(lines):
            title = lines[i].rstrip()
            underline = lines[i + 1].strip()
            if (
                _is_adornment_line(underline)
                and title.strip()
                and len(underline) >= len(title.strip())
            ):
                mark = underline[0]
                level = HEADING_LEVELS.get(mark)
                if level is not None:
                    return level, title.strip(), 2

        # Form 2: overline + title + underline
        if i + 2 >= len(lines):
            return None

        overline = lines[i].strip()
        title = lines[i + 1].rstrip()
        underline = lines[i + 2].strip()
        if not _is_adornment_line(overline) or not _is_adornment_line(underline):
            return None
        if overline[0] != underline[0]:
            return None
        if not title.strip():
            return None

        mark = overline[0]
        level = HEADING_LEVELS.get(mark)
        if level is None:
            return None
        if len(overline) < len(title.strip()) or len(underline) < len(title.strip()):
            return None

        return level, title.strip(), 3
