# Usage Guide

## Chunking Documents

radrags provides a `Chunk` dataclass to represent individual pieces of text extracted from a document.

::: radrags.chunker.Chunk
    options:
      show_source: false

## RST Chunking

`RstChunker` splits reStructuredText files into chunks by detecting section headings and grouping the content beneath them.

### Heading Detection

RST uses "adornment" lines — rows of repeated punctuation characters — to mark headings. Two forms are supported:

**Form 1** — title with underline (most common):

```rst
WireGuard
=========
```

**Form 2** — overline + title + underline (typically for top-level document titles):

```rst
##########
VPN Guide
##########
```

The adornment character determines the heading level via the `HEADING_LEVELS` map:

| Character | Level |
|-----------|-------|
| `#`       | 1     |
| `=`       | 2     |
| `*`       | 2     |
| `-`       | 3     |
| `~`       | 4     |
| `^`       | 5     |
| `"`       | 6     |

### Basic Usage

```python
from radrags.chunker import RstChunker

chunker = RstChunker()
chunks = chunker.chunk(open("wireguard.rst").read())
for c in chunks:
    print(c.heading, c.chunk_type, len(c.text))
```

::: radrags.chunker.RstChunker
    options:
      show_source: false
