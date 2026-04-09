# Query Server

radrags includes a FastAPI server that exposes `ChromaStore.query()` over HTTP.

## Running

Start the server with:

```bash
uv run python -m radrags --config radrags.ini
```

The server binds to `0.0.0.0:8000` by default. All settings can be overridden via CLI flags:

```bash
uv run python -m radrags --config radrags.ini --port 9000 --collection my_docs
```

## Configuration

Copy the example config and edit as needed:

```bash
cp radrags.ini.example radrags.ini
```

```ini
[radrags]
db_path = ./chroma_db
collection = radrags
embedding_model = nomic-embed-text
ollama_host = http://127.0.0.1:11434
host = 0.0.0.0
port = 8000
```

All keys are optional — defaults are used for any missing key.

## Endpoints

### POST /query

Search the vector store for chunks similar to the query text.

**Request:**

```json
{"query": "configure wireguard interface", "top_k": 5}
```

- `query` — non-empty search string (required)
- `top_k` — number of results, 1–100 (default 5)

**Response:**

```json
{
  "query": "configure wireguard interface",
  "results": [
    {
      "rank": 1,
      "text": "WireGuard is a fast VPN tunnel...",
      "distance": 0.23,
      "score": 0.77,
      "metadata": {
        "source_file": "configuration/interfaces/wireguard.rst",
        "heading_path": "WireGuard",
        "chunk_type": "prose",
        "token_count_estimate": 42,
        "content_hash": "abc...",
        "embedding_model": "nomic-embed-text"
      }
    }
  ],
  "count": 1
}
```

- `score` = `1.0 - distance` (higher is more similar)
- `rank` = 1-based position

### GET /health

Returns `{"status": "ok"}`.

## Docker

Build and run the server in a container:

```bash
docker compose up -d
```

This uses `network_mode: host` so the container can reach Ollama on the host machine. The `chroma_db/` directory and `radrags.ini` are volume-mounted.

To build without compose:

```bash
docker build -t radrags .
docker run --network host \
  -v ./chroma_db:/app/chroma_db \
  -v ./radrags.ini:/etc/radrags/radrags.ini:ro \
  radrags
```

## ChromaDB Persistence

ChromaDB stores data as a SQLite file plus parquet files inside `chroma_db/`. The database survives restarts. To back it up, copy the entire `chroma_db/` directory.
