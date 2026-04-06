from dataclasses import dataclass


@dataclass
class Chunk:
    heading: str
    chunk_type: str
    text: str
    source: str
