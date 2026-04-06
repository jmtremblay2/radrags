# Doc-tree Traversal

When you have a full documentation tree on disk (e.g. a cloned Sphinx project), use `chunk_docs` to recursively discover and chunk every `.rst` file in one call.

## Basic Usage

```python
from pathlib import Path
from radrags.chunker import chunk_docs

chunks = chunk_docs(Path("vendor/vyos-documentation/docs"))
print(f"Found {len(chunks)} chunks")
for c in chunks[:3]:
    print(f"  {c.source}  {c.heading}")
```

Each returned `Chunk` has its `source` field set to the file path relative to the docs root (e.g. `configuration/interfaces/wireguard.rst`). Paths always use forward slashes and are never absolute.

## Custom Chunker

By default `chunk_docs` uses an `RstChunker` with default parameters. Pass your own instance to control chunk size and overlap:

```python
from radrags.chunker import RstChunker, chunk_docs

chunker = RstChunker(chunk_size=1000, chunk_overlap=80)
chunks = chunk_docs(Path("docs/"), chunker=chunker)
```

## API Reference

::: radrags.chunker.chunk_docs
    options:
      show_source: false
