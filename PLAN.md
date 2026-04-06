# radrags — Implementation Plan

Each step follows Red/Green TDD: write a failing test, then the minimal code to pass.

---

## Test Data: VyOS Documentation

The RST chunker is developed and tested against the **VyOS documentation**, an open-source reStructuredText project:

- **GitHub**: <https://github.com/vyos/vyos-documentation>

### Setup

Run `./scripts/clone_vyos_docs.sh` to clone the repo into `vendor/vyos-documentation/`. This directory is gitignored — it is not checked into the repo.

### Test fixtures via `conftest.py`

`tests/conftest.py` defines pytest fixtures that load example RST files from the cloned VyOS docs. This avoids copying large files into the test tree and keeps tests against real-world documents:

- **`wireguard_rst`** — `vendor/vyos-documentation/docs/configuration/interfaces/wireguard.rst` (435 lines). A medium-complexity page with headings, code blocks, field lists, labels, and `cmdinclude` directives. Used as the golden-file target for `RstChunker`.
- **`firewall_rst`** — `vendor/vyos-documentation/docs/configuration/firewall/index.rst` (227 lines). A shorter page useful for edge-case and section-splitting tests.

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

## Phase 3: MarkdownChunker

### 3.1 Heading detection (Markdown)
- **Test**: `# H1`, `## H2` through `###### H6` are detected with correct levels.
- **Impl**: Heading-detection helper for Markdown `#`-style headings.

### 3.2 Front-matter stripping
- **Test**: YAML (`---`) and TOML (`+++`) front matter is removed before chunking.
- **Impl**: Strip function.

### 3.3 Reference-link & shortcode filtering
- **Test**: Reference-link definitions (`[label]: /url`) and self-closing Hugo shortcodes are dropped.
- **Impl**: Filter regexes.

### 3.4 Fenced code block pairing
- **Test**: Prose followed by a fenced code block (triple-backtick or `~~~`) merges, similar to RST prose-code pairing.
- **Impl**: Fenced-code detection and pairing.

### 3.5 Full MarkdownChunker + golden fixture
- **Test**: `MarkdownChunker().chunk(known_md)` matches a JSON fixture.
- **Impl**: Wire into `MarkdownChunker.chunk()`. Generate fixture from a reference doc (e.g. Hugo quick-start).

---

## Phase 4: Embeddings

### 4.1 Embedding function
- **Test**: Mock the Ollama client; call `get_embedding(text)` and assert it returns a `list[float]`.
- **Impl**: Add `src/radrags/embeddings.py` with `get_embedding(text, model="nomic-embed-text") -> list[float]` using the `ollama` client.

### 4.2 Embed-with-fallback (context overflow)
- **Test**: When Ollama raises a context-length error, the text is split in half and each half is embedded separately. Returns `list[tuple[str, list[float]]]`.
- **Impl**: Recursive split-and-retry logic (`embed_with_fallback`).

---

## Phase 5: Vector Store (ChromaDB)

### 5.1 VectorStore ABC
- **Test**: Subclassing without implementing required methods raises `TypeError`.
- **Impl**: Add `src/radrags/vectorstore.py` with abstract `VectorStore` defining `upsert(chunks, embeddings, metadatas)` and `query(embedding, n_results)`.

### 5.2 ChromaDB adapter
- **Test**: Using a transient in-memory ChromaDB client, upsert chunks and query by embedding. Assert correct results returned.
- **Impl**: `ChromaStore` class wrapping `chromadb.Client()`.

### 5.3 Metadata & ID generation
- **Test**: Chunk IDs are deterministic SHA256 hashes. Metadata includes `source_file`, `heading_path`, `chunk_type`, `content_hash`, `split_index`, `split_total`.
- **Impl**: Helper to build metadata dicts and IDs.

### 5.4 Pre-embedding split (`split_for_embedding`)
- **Test**: Chunks exceeding `max_embed_chars` are split at paragraph boundaries with overlap. Short chunks pass through unchanged.
- **Impl**: Function in `embeddings.py` or a shared utility.

---

## Phase 6: Search (shape TBD)

Deferred — the API shape will be decided once Phases 1–5 are working. Placeholder:
- A function or class that takes a query string, embeds it via `get_embedding`, queries the vector store, and returns a standardized result list with `text`, `metadata`, and `relevance`.

---

## Sequencing notes

- Phases 1–3 (chunker) have **zero external deps** and can be developed and tested without Ollama or ChromaDB running.
- Phases 4–5 need Ollama and ChromaDB but tests will mock network calls where possible.
- Phase 6 is intentionally deferred.
