# Vector Store

`ChromaStore` wraps a ChromaDB collection and an Ollama embedding client. Chunks are embedded on `add()` and queries embed on the fly.

## Setup

Requires a running [Ollama](https://ollama.ai) server with `nomic-embed-text`:

```bash
ollama pull nomic-embed-text
```

## Basic Usage

```python
from radrags.chunker import Chunk
from radrags.vectorstore import ChromaStore

store = ChromaStore(collection="my_docs")

# Embed and store chunks
chunks = [
    Chunk("WireGuard", "prose",
          "WireGuard is a fast VPN tunnel.",
          "interfaces/wireguard.rst"),
]
store.add(chunks)

# Query for similar chunks
results = store.query("VPN tunnel setup", top_k=3)
for r in results:
    print(f"{r['distance']:.4f}  {r['text'][:60]}")
```

## Embedding

The `embed()` method is exposed for learning and debugging:

```python
vec = store.embed("hello world")
print(len(vec))  # 768
```

## In-Memory Store

Pass `db_path=None` for an ephemeral in-memory database (useful for tests):

```python
store = ChromaStore(db_path=None, collection="ephemeral")
```

## Worst Match

Use `worst=True` to find the *least* similar chunks — useful for verifying embedding quality:

```python
worst = store.query("VPN tunnel", top_k=1, worst=True)
```

## Rebuild

Pass `rebuild=True` to wipe the collection before use:

```python
store = ChromaStore(collection="my_docs", rebuild=True)
```

## Oversized Chunks

Chunks exceeding `max_embed_chars` (default 6000) are automatically split at paragraph boundaries before embedding. All sub-vectors share the same `content_hash` in metadata so they can be traced back to the original chunk.

## Metadata Schema

Each vector stored in ChromaDB carries this metadata:

| Field | Description |
|-------|-------------|
| `source_file` | Relative path to the source document |
| `heading_path` | Breadcrumb string (e.g. `"WireGuard > Keypairs"`) |
| `chunk_type` | `"prose"` or `"code"` |
| `token_count_estimate` | `len(text) // 4` |
| `content_hash` | SHA-256 of the original chunk text |
| `embedding_model` | Name of the Ollama model used |

## API Reference

::: radrags.vectorstore.ChromaStore
    options:
      show_source: false
