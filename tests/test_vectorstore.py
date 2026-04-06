import pytest

from radrags.chunker import Chunk
from radrags.vectorstore import ChromaStore


def _ollama_available() -> bool:
    """Return True if Ollama is reachable on localhost."""
    try:
        import ollama

        ollama.Client(host="http://127.0.0.1:11434").list()
        return True
    except Exception:
        return False


requires_ollama = pytest.mark.skipif(
    not _ollama_available(), reason="Ollama not reachable"
)


# ---------------------------------------------------------------------------
# 4.1 — Embed text via Ollama
# ---------------------------------------------------------------------------


class TestEmbed:
    """Tests for ChromaStore.embed()."""

    @requires_ollama
    def test_embed_returns_float_list(self):
        store = ChromaStore(collection="test_embed")
        result = store.embed("hello world")
        assert isinstance(result, list)
        assert len(result) == 768
        assert all(isinstance(v, float) for v in result)

    @requires_ollama
    def test_embed_different_texts_differ(self):
        store = ChromaStore(collection="test_embed")
        a = store.embed("python programming language")
        b = store.embed("french baguette recipe")
        assert a != b


# ---------------------------------------------------------------------------
# 4.2 — Add and retrieve chunks
# ---------------------------------------------------------------------------


SAMPLE_CHUNKS = [
    Chunk(
        heading="WireGuard",
        chunk_type="prose",
        text="WireGuard is an extremely simple yet fast and modern VPN.",
        source="configuration/interfaces/wireguard.rst",
    ),
    Chunk(
        heading="Firewall",
        chunk_type="prose",
        text="The firewall module provides stateful packet filtering.",
        source="configuration/firewall/index.rst",
    ),
    Chunk(
        heading="BGP",
        chunk_type="prose",
        text="BGP is the routing protocol that glues the internet together.",
        source="configuration/protocols/bgp.rst",
    ),
]


class TestAddAndRetrieve:
    """Tests for ChromaStore.add() and query()."""

    @requires_ollama
    def test_add_and_query_top1(self):
        store = ChromaStore(db_path=None, collection="test_add_query")
        store.add(SAMPLE_CHUNKS)
        results = store.query("VPN tunnel WireGuard", top_k=1)
        assert len(results) == 1
        assert "WireGuard" in results[0]["text"]

    @requires_ollama
    def test_query_returns_metadata(self):
        store = ChromaStore(db_path=None, collection="test_meta")
        store.add(SAMPLE_CHUNKS)
        results = store.query("fast VPN", top_k=1)
        meta = results[0]["metadata"]
        assert meta["source_file"] == "configuration/interfaces/wireguard.rst"
        assert meta["heading_path"] == "WireGuard"
        assert meta["chunk_type"] == "prose"
        assert meta["embedding_model"] == "nomic-embed-text"

    @requires_ollama
    def test_query_returns_distance(self):
        store = ChromaStore(db_path=None, collection="test_dist")
        store.add(SAMPLE_CHUNKS)
        results = store.query("VPN tunnel", top_k=1)
        assert "distance" in results[0]
        assert isinstance(results[0]["distance"], float)
