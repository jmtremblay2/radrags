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
- From the current git tag (e.g. tag `v1.2.3` → version `1.2.3`)
- Falls back to `0.0.0` if no tag is present
- Appends `+<short git hash>` if the working tree is dirty (e.g. `0.0.0+a1b2c3d`)

Artifacts are placed in `dist/`.
