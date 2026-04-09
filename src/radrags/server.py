"""FastAPI query server for radrags ChromaStore."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Incoming query payload."""

    query: str
    top_k: int = 5


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

    return app
