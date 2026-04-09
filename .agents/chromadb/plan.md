# ChromaDB Query Server — Implementation Plan

Based on answers in `spec.md`.

## Summary

Add a FastAPI server (`radrags.server`) that exposes the existing `ChromaStore.query()` over HTTP. Configuration via INI file. Dockerized for deployment, talking to bare-metal Ollama on the host.

---

## Phase 1 — Server module & query endpoint

Branch: `feat/phase-chromadb-server`

### Step 1: Config loader

Add `radrags/config.py` — reads an INI file and returns a dataclass/dict with:
- `db_path` (default `./chroma_db`)
- `collection` (default `radrags`)
- `embedding_model` (default `nomic-embed-text`)
- `ollama_host` (default `http://127.0.0.1:11434`)
- `host` (default `0.0.0.0`)
- `port` (default `8000`)

Test: load a sample INI, assert each field is populated correctly. Also test defaults when file is missing or keys are absent.

### Step 2: POST /query endpoint

Add `radrags/server.py` — FastAPI app with a single route:

```
POST /query
Body: {"query": "...", "top_k": 5}
Response: {
  "query": "...",
  "results": [
    {
      "rank": 1,
      "text": "...",
      "distance": 0.23,
      "score": 0.77,
      "metadata": {
        "source_file": "...",
        "heading_path": "...",
        "chunk_type": "prose",
        "token_count_estimate": 42,
        "content_hash": "abc...",
        "embedding_model": "nomic-embed-text"
      }
    },
    ...
  ],
  "count": 5
}
```

- `score` = `1.0 - distance` (normalized similarity — useful for agent thresholding)
- `rank` = 1-based position
- `count` = number of results returned

Test: use FastAPI `TestClient` with a mocked/patched `ChromaStore` — assert response shape, status code 200, correct number of results.

### Step 3: GET /health endpoint

Returns `{"status": "ok"}`. Later can check Ollama + ChromaDB reachability.

Test: `TestClient` GET `/health`, assert 200 and body.

### Step 4: Validation & error handling

- `query` must be a non-empty string → 422
- `top_k` must be 1–100, default 5 → 422 if out of range
- Ollama unreachable → 503 with message
- Empty collection → 200 with empty results list

Test: send bad payloads, assert correct status codes and error shapes.

### Step 5: Wire config to server startup

Add `radrags.server:create_app(config_path)` factory. Add a `__main__.py` or entry in server.py so the server can be launched with:

```
uv run python -m radrags.server --config radrags.ini
```

Test: integration-level — create a temp INI, call `create_app`, verify the app is configured correctly (db_path, collection, etc.).

---

## Phase 2 — Packaging & deployment

### Step 6: Add dependencies to pyproject.toml

Add `fastapi` and `uvicorn[standard]` to `[project.dependencies]`.
Add `httpx` to dev deps (needed by FastAPI TestClient).

Verify: `uv sync && uv run python -c "from radrags.server import app"`.

### Step 7: Default config file

Ship a `radrags.ini.example` at repo root with commented defaults.

### Step 8: Dockerfile

Single-stage Dockerfile:
- Based on `python:3.11-slim`
- Installs the package with `uv`
- Copies `chroma_db/` (or mounts as volume)
- `CMD`: `uv run python -m radrags.server --config /etc/radrags/radrags.ini`
- Expects Ollama on the host (`host.docker.internal` or `--network host`)

### Step 9: docker-compose.yml

Single service (`radrags-server`), volume-mounts `chroma_db/` and config, `network_mode: host` so it can reach Ollama.

### Step 10: Docs

- `docs/guide/server.md` — how to run, configure, query, and deploy.
- Document ChromaDB persistence model (it's just a SQLite file + parquet in `chroma_db/`; survives restarts, back it up by copying the directory).

---

## Decisions captured

| Decision | Choice |
|---|---|
| Framework | FastAPI |
| Module location | `src/radrags/server.py` |
| Config format | INI file |
| Scope | Query-only (no add endpoint) |
| Ollama | Bare metal on host, server calls it directly |
| Docker | Server container only, `--network host` to reach Ollama |
| Collections | Single collection for now |
| Auth | None (out of scope) |
