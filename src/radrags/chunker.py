"""Document chunking primitives.

Provides the ``Chunk`` dataclass, a ``DocumentChunker`` ABC, and a
concrete ``RstChunker`` for reStructuredText files.  Heading-level
constants and helper functions used by the chunkers are also exported.
"""

import re
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


_CODE_DIRECTIVE_RE = re.compile(r"^\s*\.\.\s+(?:code-block|parsed-literal|code)::")


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

    def __init__(self, chunk_size: int = 2000, chunk_overlap: int = 120) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be >= 0")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

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

    def _split_sections(
        self, lines: Sequence[str]
    ) -> list[tuple[list[str], list[str]]]:
        """Parse RST *lines* into ``(heading_path, content_blocks)`` tuples.

        Walks the line sequence once.  When a heading is detected the
        current section is closed and the heading stack is updated so
        that child headings carry their full ancestor path.

        Args:
            lines: Full document split into individual lines.

        Returns:
            List of ``(heading_path, content_blocks)`` pairs where
            *heading_path* is the ordered list of ancestor heading
            titles (e.g. ``["WireGuard", "Keypairs"]``) and
            *content_blocks* is a list of non-empty text blocks for
            that section.
        """
        sections: list[tuple[list[str], list[str]]] = []
        heading_stack: list[tuple[int, str]] = []
        current_blocks: list[str] = []
        prose_buffer: list[str] = []

        def flush_prose() -> None:
            if prose_buffer:
                block = "\n".join(prose_buffer).strip()
                if block:
                    current_blocks.append(block)
                prose_buffer.clear()

        def flush_section() -> None:
            flush_prose()
            if current_blocks:
                path = [title for _, title in heading_stack]
                sections.append((path, current_blocks.copy()))
                current_blocks.clear()

        i = 0
        while i < len(lines):
            heading_info = self._heading_at(lines, i)
            if heading_info is not None:
                level, title, consumed = heading_info
                flush_section()
                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()
                heading_stack.append((level, title))
                i += consumed
                continue

            prose_buffer.append(lines[i])
            i += 1

        flush_section()
        return sections

    def _is_metadata_only(self, block: str) -> bool:
        """Return ``True`` if *block* contains only RST metadata.

        Metadata blocks include field lists (``:lastproofread:``),
        RST labels (``.. _wireguard:``), anonymous targets (``__ …``),
        and figure/image directives.  These carry no retrievable
        documentation content.

        Operational directives like ``.. opcmd::`` and ``.. cfgcmd::``
        are **not** metadata — they document commands and are kept.

        Args:
            block: A single text block from ``_split_sections``.

        Returns:
            True if the block should be dropped, False otherwise.
        """
        trimmed = block.strip()
        if not trimmed:
            return True
        if trimmed.startswith(":") and ":" in trimmed[1:]:
            return True
        if trimmed.startswith(".. _"):
            return True
        if trimmed.startswith("__ "):
            return True
        if re.match(r"\.\.\s+(?:figure|image)::", trimmed):
            return True
        return False

    def _pair_prose_with_code(self, blocks: list[str]) -> tuple[list[str], list[bool]]:
        """Pair each prose block with an immediately following code block.

        Keeping explanation and example together in one chunk avoids
        the retrieval problem where a query returns prose without the
        command syntax, or a code block without its description.

        Args:
            blocks: List of raw text blocks for one document section.

        Returns:
            ``(paired_blocks, was_paired_flags)`` — parallel lists
            where ``was_paired_flags[i]`` is ``True`` when
            ``paired_blocks[i]`` was formed by merging prose + code.
        """
        result: list[str] = []
        was_paired: list[bool] = []
        i = 0
        while i < len(blocks):
            block = blocks[i]
            if not _CODE_DIRECTIVE_RE.match(block.splitlines()[0]) and i + 1 < len(
                blocks
            ):
                next_block = blocks[i + 1]
                if _CODE_DIRECTIVE_RE.match(next_block.splitlines()[0]):
                    result.append(f"{block}\n\n{next_block}")
                    was_paired.append(True)
                    i += 2
                    continue
            result.append(block)
            was_paired.append(False)
            i += 1
        return result, was_paired

    def _split_prose_block(self, text: str) -> list[str]:
        """Split a long prose block at paragraph boundaries.

        Keeps whole paragraphs together up to ``self.chunk_size``.
        Falls back to word-boundary splitting via ``_hard_split_text``
        for single paragraphs that exceed the limit.

        Args:
            text: Plain prose text (no RST code directives).

        Returns:
            List of text pieces each approximately
            ``self.chunk_size`` characters or fewer.
        """
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        if not paragraphs:
            return []

        chunks: list[str] = []
        current = ""

        for para in paragraphs:
            candidate = para if not current else f"{current}\n\n{para}"
            if len(candidate) <= self.chunk_size:
                current = candidate
                continue
            if current:
                chunks.append(current)
                current = ""
            if len(para) <= self.chunk_size:
                current = para
                continue
            pieces = self._hard_split_text(para)
            chunks.extend(pieces[:-1])
            current = pieces[-1] if pieces else ""

        if current:
            chunks.append(current)
        return chunks

    def _hard_split_text(self, text: str) -> list[str]:
        """Split *text* at word boundaries as a last resort.

        Used inside ``_split_prose_block`` when a single paragraph
        exceeds ``self.chunk_size``.  Prefers the last space within
        the target window to avoid cutting mid-word.

        Args:
            text: A single run of text without blank-line breaks.

        Returns:
            List of pieces with ``self.chunk_overlap`` characters of
            shared context between consecutive pieces.
        """
        chunks: list[str] = []
        start = 0
        step = max(1, self.chunk_size - self.chunk_overlap)

        while start < len(text):
            end = min(len(text), start + self.chunk_size)
            if end < len(text):
                split_at = text.rfind(" ", start, end)
                if split_at > start + int(self.chunk_size * 0.5):
                    end = split_at

            piece = text[start:end].strip()
            if piece:
                chunks.append(piece)
            if end >= len(text):
                break
            start = max(start + 1, end - self.chunk_overlap)

        return chunks

    def _merge_small_chunks(
        self, chunks: list[Chunk], min_size: int = 300
    ) -> list[Chunk]:
        """Merge chunks smaller than *min_size* into the preceding chunk.

        Merging backward keeps the heading metadata correct: a small
        fragment belongs to the section it came from.  Falls back to
        merging forward only when the very first chunk is tiny.

        Args:
            chunks: Ordered list of chunks.
            min_size: Character threshold below which a chunk is
                merged into its neighbour.

        Returns:
            New list with small chunks absorbed.
        """
        if len(chunks) < 2:
            return chunks

        result: list[Chunk] = []
        for chunk in chunks:
            if len(chunk.text) < min_size and result:
                prev = result[-1]
                result[-1] = Chunk(
                    heading=prev.heading,
                    chunk_type=prev.chunk_type,
                    text=f"{prev.text}\n\n{chunk.text}",
                    source=prev.source,
                )
            elif len(chunk.text) < min_size and not result:
                result.append(chunk)
            else:
                if result and len(result[-1].text) < min_size:
                    tiny = result.pop()
                    result.append(
                        Chunk(
                            heading=chunk.heading,
                            chunk_type=chunk.chunk_type,
                            text=f"{tiny.text}\n\n{chunk.text}",
                            source=chunk.source,
                        )
                    )
                else:
                    result.append(chunk)

        return result
