"""Document chunking primitives."""

from dataclasses import dataclass


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
