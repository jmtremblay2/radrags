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
