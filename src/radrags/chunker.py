"""Document chunking primitives.

Provides the ``Chunk`` dataclass, a ``DocumentChunker`` ABC, and a
concrete ``RstChunker`` for reStructuredText files.  Heading-level
constants and helper functions used by the chunkers are also exported.
"""

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
    """Abstract base class for document chunkers.

    Subclasses implement ``chunk()`` for a specific source format
    (RST, Markdown, etc.).  The interface is intentionally narrow:
    accept raw text plus an optional filesystem root for include
    resolution, and return a flat list of ``Chunk`` objects.
    """

    @abstractmethod
    def chunk(self, text: str, docs_root: Path | None = None) -> list[Chunk]:
        """Split document text into a list of chunks.

        Args:
            text: Raw source document text.
            docs_root: Filesystem root used to resolve include
                directives.  Pass ``None`` when not needed.

        Returns:
            Ordered list of ``Chunk`` objects from the document.
        """


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
    """Return True if *line* consists of a single repeated character.

    Args:
        line: A single line of text (no newline).

    Returns:
        True when every character in *line* is identical and the
        string is non-empty, False otherwise.
    """
    return bool(line) and len(set(line)) == 1


class RstChunker(DocumentChunker):
    """Chunker for reStructuredText documents.

    Splits an RST document into ``Chunk`` objects by following the
    document's heading hierarchy.  Adornment characters are mapped to
    heading levels via ``HEADING_LEVELS``.

    Example:
        ```python
        from radrags.chunker import RstChunker

        chunker = RstChunker()
        chunks = chunker.chunk(open("wireguard.rst").read())
        for c in chunks:
            print(c.heading, c.chunk_type, len(c.text))
        ```
    """

    def chunk(self, text: str, docs_root: Path | None = None) -> list[Chunk]:
        """Split RST text into chunks.

        Args:
            text: Raw RST source text.
            docs_root: Sphinx docs root for resolving ``.. include::``
                paths.  Pass ``None`` to skip include resolution.

        Returns:
            Ordered list of ``Chunk`` objects in document order.

        Example:
            Given a short RST document that uses three heading levels
            (Form 2 with ``#``, Form 1 with ``=``, and Form 1 with ``-``):

            ```rst
            #########
            WireGuard
            #########

            WireGuard is a simple yet fast VPN.

            Site to Site
            ============

            This section covers tunnels.

            Generate Keypair
            ----------------

            Run wg genkey to create a key.
            ```

            Chunking it produces one ``Chunk`` per section, each carrying
            its heading, the prose beneath it, and the source path:

            ```python
            from radrags.chunker import RstChunker

            doc = (
                "#########\\n"
                "WireGuard\\n"
                "#########\\n"
                "\\n"
                "WireGuard is a simple yet fast VPN.\\n"
                "\\n"
                "Site to Site\\n"
                "============\\n"
                "\\n"
                "This section covers tunnels.\\n"
                "\\n"
                "Generate Keypair\\n"
                "----------------\\n"
                "\\n"
                "Run wg genkey to create a key.\\n"
            )

            chunker = RstChunker()
            chunks = chunker.chunk(doc)

            assert chunks == [
                Chunk(
                    heading="WireGuard",
                    chunk_type="prose",
                    text="WireGuard is a simple yet fast VPN.",
                    source="",
                ),
                Chunk(
                    heading="Site to Site",
                    chunk_type="prose",
                    text="This section covers tunnels.",
                    source="",
                ),
                Chunk(
                    heading="Generate Keypair",
                    chunk_type="prose",
                    text="Run wg genkey to create a key.",
                    source="",
                ),
            ]
            ```
        """
        return []

    def _heading_at(self, lines: Sequence[str], i: int) -> tuple[int, str, int] | None:
        """Detect an RST heading at position *i* in *lines*.

        Handles both RST heading forms:

        - **Form 1** — title + underline (e.g. ``WireGuard`` / ``=========``).
        - **Form 2** — overline + title + underline.

        The adornment character is looked up in ``HEADING_LEVELS`` to
        determine the heading depth.

        Args:
            lines: Full document split into individual lines.
            i: Zero-based index of the line to inspect.

        Returns:
            A ``(level, title, lines_consumed)`` tuple on match,
            or ``None`` if the position is not a heading.

        Example:
            Consider this excerpt adapted from the VyOS WireGuard page.
            It uses three heading forms found in real RST documentation:

            ```rst
            #########
            WireGuard
            #########

            WireGuard is an extremely simple yet fast and modern VPN.

            ****************
            Site to Site VPN
            ****************

            This section covers site-to-site tunnels.

            Generate Keypair
            ================

            To generate a WireGuard keypair, run:

            Server Configuration
            --------------------

            Configure the local side of the tunnel.
            ```

            Scanning line by line with ``_heading_at`` yields:

            ```python
            from radrags.chunker import RstChunker

            doc = (
                "#########\\n"
                "WireGuard\\n"
                "#########\\n"
                "\\n"
                "WireGuard is an extremely simple yet fast and modern VPN.\\n"
                "\\n"
                "****************\\n"
                "Site to Site VPN\\n"
                "****************\\n"
                "\\n"
                "This section covers site-to-site tunnels.\\n"
                "\\n"
                "Generate Keypair\\n"
                "================\\n"
                "\\n"
                "To generate a WireGuard keypair, run:\\n"
                "\\n"
                "Server Configuration\\n"
                "--------------------\\n"
                "\\n"
                "Configure the local side of the tunnel.\\n"
            )

            chunker = RstChunker()
            lines = doc.splitlines()

            headings = []
            i = 0
            while i < len(lines):
                result = chunker._heading_at(lines, i)
                if result is not None:
                    level, title, consumed = result
                    headings.append((level, title, consumed))
                    i += consumed
                else:
                    i += 1

            assert headings == [
                (1, "WireGuard", 3),           # Form 2, # adornment → level 1
                (2, "Site to Site VPN", 3),     # Form 2, * adornment → level 2
                (2, "Generate Keypair", 2),     # Form 1, = adornment → level 2
                (3, "Server Configuration", 2), # Form 1, - adornment → level 3
            ]
            ```
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
