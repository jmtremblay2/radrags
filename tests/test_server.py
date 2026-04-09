"""Tests for radrags.server — FastAPI query server."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from radrags.server import create_app


@pytest.fixture()
def mock_store() -> MagicMock:
    store = MagicMock()
    store.query.return_value = [
        {
            "text": "WireGuard is a fast VPN.",
            "metadata": {
                "source_file": "interfaces/wireguard.rst",
                "heading_path": "WireGuard",
                "chunk_type": "prose",
                "token_count_estimate": 6,
                "content_hash": "abc123",
                "embedding_model": "nomic-embed-text",
            },
            "distance": 0.25,
        },
        {
            "text": "Configure a WireGuard tunnel.",
            "metadata": {
                "source_file": "interfaces/wireguard.rst",
                "heading_path": "WireGuard > Configuration",
                "chunk_type": "prose",
                "token_count_estimate": 7,
                "content_hash": "def456",
                "embedding_model": "nomic-embed-text",
            },
            "distance": 0.40,
        },
    ]
    return store


@pytest.fixture()
def client(mock_store: MagicMock) -> TestClient:
    app = create_app(store=mock_store)
    return TestClient(app)


class TestPostQuery:
    """POST /query returns ranked results from ChromaStore."""

    def test_returns_200_with_results(
        self, client: TestClient, mock_store: MagicMock
    ) -> None:
        resp = client.post("/query", json={"query": "wireguard vpn", "top_k": 2})
        assert resp.status_code == 200
        body = resp.json()
        assert body["query"] == "wireguard vpn"
        assert body["count"] == 2
        assert len(body["results"]) == 2

        first = body["results"][0]
        assert first["rank"] == 1
        assert first["text"] == "WireGuard is a fast VPN."
        assert first["distance"] == 0.25
        assert first["score"] == pytest.approx(0.75)
        assert first["metadata"]["source_file"] == "interfaces/wireguard.rst"

        mock_store.query.assert_called_once_with("wireguard vpn", top_k=2)

    def test_default_top_k_is_5(
        self, client: TestClient, mock_store: MagicMock
    ) -> None:
        client.post("/query", json={"query": "something"})
        mock_store.query.assert_called_once_with("something", top_k=5)


class TestHealthEndpoint:
    """GET /health returns status ok."""

    def test_health_returns_ok(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestQueryValidation:
    """POST /query rejects bad input and handles backend errors."""

    def test_empty_query_returns_422(self, client: TestClient) -> None:
        resp = client.post("/query", json={"query": "", "top_k": 5})
        assert resp.status_code == 422

    def test_missing_query_returns_422(self, client: TestClient) -> None:
        resp = client.post("/query", json={"top_k": 5})
        assert resp.status_code == 422

    def test_top_k_zero_returns_422(self, client: TestClient) -> None:
        resp = client.post("/query", json={"query": "test", "top_k": 0})
        assert resp.status_code == 422

    def test_top_k_over_100_returns_422(self, client: TestClient) -> None:
        resp = client.post("/query", json={"query": "test", "top_k": 101})
        assert resp.status_code == 422

    def test_ollama_unreachable_returns_503(
        self,
        mock_store: MagicMock,
    ) -> None:
        mock_store.query.side_effect = ConnectionError("Ollama down")
        app = create_app(store=mock_store)
        c = TestClient(app, raise_server_exceptions=False)
        resp = c.post("/query", json={"query": "test"})
        assert resp.status_code == 503
        assert "error" in resp.json()

    def test_empty_collection_returns_200_empty(
        self,
        mock_store: MagicMock,
    ) -> None:
        mock_store.query.return_value = []
        app = create_app(store=mock_store)
        c = TestClient(app)
        resp = c.post("/query", json={"query": "test"})
        assert resp.status_code == 200
        assert resp.json()["results"] == []
        assert resp.json()["count"] == 0
