# radrags

RAG experiments — chunking, embedding, and vector search from scratch.

## Quick Example

Given a small RST document with three heading levels:

```rst
#########
WireGuard
#########

WireGuard is a simple yet fast VPN that uses state-of-the-art
cryptography. It aims to be faster and simpler than IPsec ...

Generate Keypair
================

WireGuard requires the generation of a keypair ...

.. code-block:: shell

   $ generate pki wireguard key-pair

Server Configuration
--------------------

Each side of the WireGuard tunnel needs a private key ...
```

`RstChunker` splits it into three chunks that follow the heading hierarchy:

```python
from radrags.chunker import RstChunker

chunker = RstChunker()
chunks = chunker.chunk(open("wireguard.rst").read())

for c in chunks:
    print(c.heading, "|", c.chunk_type)

# WireGuard | prose
# WireGuard > Generate Keypair | prose     (code block paired with its prose)
# WireGuard > Generate Keypair > Server Configuration | prose
```

See `test_rst_chunker_end_to_end` in the test suite for the full
input document and exact expected output.

## Setup

```bash
uv sync --extra dev
```

## Tests

```bash
uv run pytest
```

## Formatting

```bash
uv run black .
```

## Build

Build a wheel package:

```bash
./build.sh
```

## Documentation

Build the docs (static site output in `site/`):

```bash
./docs.sh
```

Live preview while editing:

```bash
./docs.sh --open
```

## Examples

Index the VyOS 1.4.3 docs into ChromaDB and query them (requires Ollama with `nomic-embed-text`):

```bash
./scripts/clone_vyos_docs.sh              # clone VyOS docs (one-time)
uv run python examples/vyos_index.py --build-index   # embed all RST files
uv run python examples/vyos_index.py set up wireguard interface          # top 3 matches
uv run python examples/vyos_index.py --top 5 set up wireguard interface  # top 5
uv run python examples/vyos_index.py --top 2 --worst set up wireguard interface  # worst 2
```

What to track in git:

| Path | Tracked | Notes |
|------|---------|-------|
| `docs/` | Yes | Hand-written Markdown pages and `:::` directives |
| `mkdocs.yml` | Yes | MkDocs configuration |
| `docs.sh` | Yes | Build/serve script |
| `src/**/*.py` docstrings | Yes | Single source of truth for API docs |
| `site/` | No | Generated output — in `.gitignore` |

The version is determined automatically:
- From the current git tag if HEAD is at a tag (e.g. tag `v1.2.3` → version `1.2.3`)
- Otherwise `0.0.0+<hash>` (e.g. `0.0.0+a1b2c3d`)
- Appends `.dirty` / `+dirty` if there are uncommitted changes (e.g. `1.2.3+dirty` or `0.0.0+a1b2c3d.dirty`)

Artifacts are placed in `dist/`.
