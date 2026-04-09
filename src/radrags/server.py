"""FastAPI query server for radrags ChromaStore."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Incoming query payload."""

    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=100)


class ResultItem(BaseModel):
    """Single search result."""

    rank: int
    text: str
    distance: float
    score: float
    metadata: dict[str, Any]


class QueryResponse(BaseModel):
    """Response for POST /query."""

    query: str
    results: list[ResultItem]
    count: int


def create_app(store: Any = None) -> FastAPI:
    """Build the FastAPI application.

    Args:
        store: A ``ChromaStore`` instance (or mock) used to serve queries.

    Returns:
        Configured ``FastAPI`` application.
    """
    app = FastAPI(title="radrags")
    app.state.store = store

    @app.exception_handler(ConnectionError)
    async def connection_error_handler(
        request: Any, exc: ConnectionError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"error": str(exc)},
        )

    @app.post("/query", response_model=QueryResponse)
    def query_endpoint(req: QueryRequest) -> QueryResponse:
        raw_results = app.state.store.query(req.query, top_k=req.top_k)
        results = [
            ResultItem(
                rank=i + 1,
                text=r["text"],
                distance=r["distance"],
                score=1.0 - r["distance"],
                metadata=r["metadata"],
            )
            for i, r in enumerate(raw_results)
        ]
        return QueryResponse(query=req.query, results=results, count=len(results))

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def create_app_from_config(config_path: str | None = None) -> FastAPI:
    """Build a FastAPI app wired to a real ChromaStore via INI config.

    Args:
        config_path: Path to an INI config file, or ``None`` for defaults.

    Returns:
        Configured ``FastAPI`` application backed by ``ChromaStore``.
    """
    from radrags.config import load_config
    from radrags.vectorstore import ChromaStore

    cfg = load_config(config_path)
    store = ChromaStore(
        db_path=cfg.db_path,
        collection=cfg.collection,
        embedding_model=cfg.embedding_model,
        ollama_host=cfg.ollama_host,
    )
    return create_app(store=store)
