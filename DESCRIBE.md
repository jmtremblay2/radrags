# radrags

## Goal

Understand embeddings, vector search, and RAG by building a chunking/indexing/search pipeline from scratch. This package organizes experiments and provides working examples. May switch to a formal framework later.

## Architecture

### Chunker
- Abstract interface (`DocumentChunker` ABC) with concrete implementations per format.
- First implementation: `RstChunker` (ported from `vyosindex/scripts/chunker.py`).
- Parameterized so benchmarked outputs remain reproducible across changes.

### Vector Store
- First engine: ChromaDB (concrete class, no ABC yet — add interface when a second engine appears).

### Embeddings
- All embeddings come from Ollama via the `ollama` Python library.
- Default model: `nomic-embed-text` (768-dimensional vectors).
- Oversized text that exceeds the model's context length is split at paragraph boundaries with overlap, then each piece is embedded separately. If a piece still overflows, binary-split and retry recursively (see `embed_with_fallback` in `vyosindex/scripts/chroma.py`).

### Package Structure
- Flat sub-modules: `radrags.chunker`, `radrags.vectorstore`.
- Embedding logic lives inside `radrags.vectorstore` (exposed for learning). Separate `radrags.embeddings` module only if needed later.
- Library only — no CLI entry points.

### Dependencies
- `ollama` and `chromadb` are required dependencies in `[project.dependencies]`.

### Chunk Dataclass
- Minimal: `heading: str`, `chunk_type: str`, `text: str`, `source: str` — same shape as the reference prototypes.
- `source` is the relative path to the file that produced the chunk (e.g. `configuration/interfaces/wireguard.rst`).

### ID Strategy
- Each chunk is identified by `sha256(text)` — used as the ChromaDB document ID.
- This makes upserts idempotent: same text → same hash → re-indexing is a no-op.
- No UUIDs, no hand-crafted IDs.

### Metadata Schema (per chunk in ChromaDB)
- `source_file`: relative path to source file within the docs root.
- `heading_path`: breadcrumb string (e.g. `"WireGuard > Keypairs"`).
- `chunk_type`: `"prose"` or `"code"`.
- `token_count_estimate`: `len(text) // 4`.
- `content_hash`: SHA-256 of original chunk text (before any embedding splits).
- `embedding_model`: name of the model used to generate the embedding.

## Out of Scope (for now)
- MarkdownChunker — de-prioritized; RST only.
- LLM generation / answer synthesis (the `call_ollama` RAG pipeline) — retrieval only.
- Reranking (lexical overlap, heuristic boosting) — just distance-based ranking.
- CLI entry points — library only.
- Config files — all config via function/class arguments.

## Testing / Benchmarking

- Chunk known documents, save output as JSON fixtures.
- pytest asserts the chunker reproduces the fixture exactly.
- If chunking logic changes, parameterize (or subclass) so previous benchmarks still pass.

## Reference

`vyosindex/scripts/*.py` contains a disorganized set of prototypes (chunker ABC, `RstChunker`, ChromaDB integration, CLI preview) along with some other tangentially related scripts.


## Pending Features

### Doc-tree Traversal (`radrags.chunker`)
- Function that takes a local folder root, recursively finds all `*.rst` files, chunks each one, and yields/returns a flat list of `Chunk` objects.
- Populates `Chunk.source` with the file path relative to the docs root.
- RST only for now.

### Vector Store (`radrags.vectorstore`)
- Concrete `ChromaStore` class wrapping ChromaDB. No ABC yet — refactor to an interface when a second engine is needed.
- **Constructor args**: `db_path` (default `./chroma_db/`), `collection` name, `embedding_model` (default `nomic-embed-text`), `ollama_host` (default `http://127.0.0.1:11434`).
- **`add(chunks)`** — embed and upsert a list of `Chunk` objects. Computes embeddings automatically; also expose a standalone `embed(text) → list[float]` method for learning/debugging.
- **`query(text, top_k) → list[result]`** — embed the query, return top-k matches by cosine distance. Each result includes the chunk text, metadata, and distance. Also support returning the farthest match (worst match = highest distance).
- **Collection management** — `get_or_create_collection` by default; `rebuild=True` deletes and recreates.
- **Oversized chunks** — split text > `max_embed_chars` (default 6000) at paragraph boundaries with overlap before embedding. Binary-split fallback on context-length overflow (see `embed_with_fallback` in `vyosindex/scripts/chroma.py`).
