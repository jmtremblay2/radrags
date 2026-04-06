# radrags

RAG experiments.

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

The version is determined automatically:
- From the current git tag if HEAD is at a tag (e.g. tag `v1.2.3` → version `1.2.3`)
- Otherwise `0.0.0+<hash>` (e.g. `0.0.0+a1b2c3d`)
- Appends `.dirty` / `+dirty` if there are uncommitted changes (e.g. `1.2.3+dirty` or `0.0.0+a1b2c3d.dirty`)

Artifacts are placed in `dist/`.
