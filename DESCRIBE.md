# radrags

## Goal

Understand embeddings, vector search, and RAG by building a chunking/indexing/search pipeline from scratch. This package organizes experiments and provides working examples. May switch to a formal framework later.

## Architecture

### Chunker
- Abstract interface (`DocumentChunker` ABC) with concrete implementations per format.
- First implementation: `RstChunker` (ported from `vyosindex/scripts/chunker.py`).
- Parameterized so benchmarked outputs remain reproducible across changes.

### Vector Store
- Behind an abstract interface so engines are swappable (write an adapter for each).
- First engine: ChromaDB.

### Embeddings
- All embeddings come from Ollama.

### Search
- Returns a list (or generator) of standardized results with at minimum: text, metadata, and relevance info.

### Inputs
- Text-based only. RST first, then Markdown (Hugo-flavored).
- Adapters for other formats (HTML, etc.) are secondary scope.

### Configuration
- All configuration via function/class arguments. No config file system for now.

### Package Structure
- Flat sub-modules: `radrags.chunker`, `radrags.vectorstore`, `radrags.search`, `radrags.embeddings`.
- Library only — no CLI entry points.

### Dependencies
- `ollama` and `chromadb` are required dependencies in `[project.dependencies]`.

### Chunk Dataclass
- Minimal: `heading: str`, `chunk_type: str`, `text: str` — same shape as the reference prototypes.

## Testing / Benchmarking

- Chunk known documents, save output as JSON fixtures.
- pytest asserts the chunker reproduces the fixture exactly.
- If chunking logic changes, parameterize (or subclass) so previous benchmarks still pass.

## Reference

`vyosindex/scripts/*.py` contains a disorganized set of prototypes (chunker ABC, `RstChunker`, ChromaDB integration, CLI preview) along with some other tangentially related scripts.