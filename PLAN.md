# radrags — Implementation Plan

Each step follows Red/Green TDD: write a failing test, then the minimal code to pass.

---

## Test Data: VyOS Documentation

The RST chunker is developed and tested against the **VyOS documentation**, an open-source reStructuredText project:

- **GitHub**: <https://github.com/vyos/vyos-documentation>
- **Pinned tag**: `1.4.3` — all tests and golden fixtures target this single release. Multi-tag indexing is out of scope for now.

### Setup

Run `./scripts/clone_vyos_docs.sh` to clone the repo at tag **1.4.3** into `vendor/vyos-documentation/`. This directory is gitignored — it is not checked into the repo. The script is idempotent: re-running it ensures the correct tag is checked out.

### Test fixtures via `conftest.py`

`tests/conftest.py` defines pytest fixtures that load example RST files from the cloned VyOS docs. The pinned tag is hardcoded as `VYOS_DOCS_TAG = "1.4.3"` in `conftest.py`. This avoids copying large files into the test tree and keeps tests against real-world documents:

- **`wireguard_rst`** — `vendor/vyos-documentation/docs/configuration/interfaces/wireguard.rst` (427 lines). A medium-complexity page with headings, code blocks, field lists, labels, and `cmdinclude` directives. Used as the golden-file target for `RstChunker`.
- **`firewall_rst`** — `vendor/vyos-documentation/docs/configuration/firewall/index.rst` (180 lines). A shorter page useful for edge-case and section-splitting tests.

Each fixture reads the file at test time and `pytest.skip()`s if `vendor/` is not cloned, so CI can optionally skip integration-style tests.

---

## Phase 1: Foundation

### 1.1 Chunk dataclass
- **Test**: Import `Chunk` from `radrags.chunker`, create an instance with `heading`, `chunk_type`, `text`. Assert fields.
- **Impl**: Add `Chunk` dataclass to `src/radrags/chunker.py`.

### 1.2 DocumentChunker ABC
- **Test**: Subclassing `DocumentChunker` without implementing `chunk()` raises `TypeError`. Subclassing with a stub `chunk()` succeeds.
- **Impl**: Add `DocumentChunker` ABC with abstract method `chunk(text: str, docs_root: Path | None = None) -> list[Chunk]`.

### 1.3 Update pyproject.toml
- Add `ollama` and `chromadb` to `[project.dependencies]`.
- Run `uv sync` to lock.

---

## Phase 2: RstChunker

### 2.1 Heading detection
- **Test**: Unit tests for RST heading detection (Form 1: underline only, Form 2: over+underline). Various adornment chars. Edge cases (too-short underline, unknown char).
- **Impl**: Heading-detection helpers in `src/radrags/chunker.py`.

### 2.2 Section splitting
- **Test**: Given a multi-section RST string, `_split_sections()` returns `[(heading_path, block_text), ...]` with correct hierarchy.
- **Impl**: Section-splitting logic that tracks heading stack and emits (heading_path, text) pairs.

### 2.3 Metadata filtering
- **Test**: Blocks containing only RST labels (`.. _foo:`), field lists (`:field:`), figures, or `.. cmdinclude::` directives are dropped.
- **Impl**: Filter function for metadata-only blocks.

### 2.4 Prose-code pairing
- **Test**: Prose followed by `.. code-block::` merges into a single chunk with `chunk_type="code"`.
- **Impl**: Pairing logic that detects `.. code-block::` and merges.

### 2.5 Prose splitting
- **Test**: An oversized prose block (> `chunk_size`) is split at paragraph boundaries, then word boundaries. Overlap is applied.
- **Impl**: Splitting function with `chunk_size` and `chunk_overlap` parameters.

### 2.6 Small chunk merging
- **Test**: Adjacent chunks under 300 chars merge backward; heading is preserved from the earlier chunk.
- **Impl**: Post-processing merge pass.

### 2.7 Full RstChunker + golden fixture
- **Test**: `RstChunker().chunk(wireguard_rst)` output matches `tests/fixtures/wireguard_chunks.json` (chunk count, headings, types, text).
- **Impl**: Wire all helpers into `RstChunker.chunk()`. Copy fixture from `vyosindex/tests/fixtures/` (or regenerate).

---

## Phase 3: Doc-tree Traversal

### 3.1 Discover RST files
- **Test**: Point `chunk_docs(docs_root)` at `vendor/vyos-documentation/docs`. Assert it returns a non-empty `list[Chunk]`, every chunk has a non-empty `source` field, and all sources end with `.rst`. Skip if vendor not cloned.
- **Impl**: Add `chunk_docs(docs_root: Path, chunker: DocumentChunker | None = None) -> list[Chunk]` to `radrags.chunker`. Recursively globs `*.rst`, chunks each file, sets `Chunk.source` to the path relative to `docs_root`.

### 3.2 Source field populated correctly
- **Test**: Chunk a single known file via `chunk_docs`. Assert every returned chunk's `source` matches the expected relative path (e.g. `configuration/interfaces/wireguard.rst`).
- **Impl**: Already wired in 3.1 — this test verifies the path logic specifically.

---

## Phase 4: Vector Store (ChromaDB)

### 4.1 Embed text via Ollama
- **Test**: Call `ChromaStore.embed("hello world")`, assert it returns a `list[float]` of length 768. Requires a running Ollama with `nomic-embed-text`. Skip if Ollama is unreachable.
- **Impl**: Add `src/radrags/vectorstore.py` with `ChromaStore` class. Constructor takes `db_path`, `collection`, `embedding_model` (default `nomic-embed-text`), `ollama_host`. Implement `embed(text) -> list[float]` using `ollama.Client.embeddings()`.

### 4.2 Add and retrieve chunks
- **Test**: Create a `ChromaStore` with an ephemeral in-memory ChromaDB client. Add a handful of hand-crafted `Chunk` objects via `add(chunks)`. Query with a string semantically close to one chunk. Assert the top-1 result contains the expected chunk text and metadata (`source_file`, `heading_path`, `chunk_type`, `embedding_model`). Requires Ollama.
- **Impl**: Implement `add(chunks)` — for each chunk, compute `sha256(text)` as the ID, embed the text, and upsert with metadata. Implement `query(text, top_k)` — embed the query, call `collection.query`, return results with text, metadata, and distance.

### 4.3 Idempotent upsert
- **Test**: `add()` the same chunks twice. Assert collection count doesn't double (same `sha256` ID → no duplicates).
- **Impl**: Already handled by using `upsert` with content-hash IDs — this test verifies it.

### 4.4 Worst match (farthest result)
- **Test**: Add several diverse chunks. Call `query(text, top_k=1, worst=True)` (or equivalent). Assert the returned chunk is the one with the highest cosine distance from the query.
- **Impl**: Implement worst-match by querying the full collection and returning the last result.

### 4.5 Rebuild collection
- **Test**: Add chunks, then construct a new `ChromaStore` with `rebuild=True`. Assert the collection is empty.
- **Impl**: When `rebuild=True`, delete the collection before calling `get_or_create_collection`.

### 4.6 Oversized chunk splitting for embedding
- **Test**: Create a chunk with text > 6000 chars. Call `add([chunk])`. Assert the collection has more than one vector (the chunk was split), and all vectors share the same `content_hash` in metadata.
- **Impl**: Before embedding, split text exceeding `max_embed_chars` at paragraph boundaries with overlap. Use `embed_with_fallback` (binary-split on context-length error) as a safety net.

---

## Phase 5: End-to-end Retrieval

### 5.1 Index real docs and query
- **Test**: Use `chunk_docs` on the VyOS vendor docs (or a small subset via `max_files`), feed chunks into `ChromaStore.add()`, then `query("how to generate wireguard keys")`. Assert the top result's `source_file` contains `wireguard` and the text mentions key generation. Requires Ollama + vendor docs.
- **Impl**: No new production code — this wires together Phases 2–4 and proves the pipeline works end to end.

---

## Phase 6: Search (shape TBD)

Deferred — the API shape will be decided once Phases 1–5 are working. Placeholder:
- A function or class that takes a query string, embeds it via `get_embedding`, queries the vector store, and returns a standardized result list with `text`, `metadata`, and `relevance`.

---

## Sequencing notes

- Phases 1–3 (chunker) have **zero external deps** and can be developed and tested without Ollama or ChromaDB running.
- Phases 4–5 need Ollama and ChromaDB but tests will mock network calls where possible.
- Phase 6 is intentionally deferred.
