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
        text=(
            "WireGuard is an extremely simple yet fast and modern VPN that "
            "utilises state-of-the-art cryptography. It aims to be faster "
            "and simpler than IPsec. WireGuard is designed as a general "
            "purpose VPN for running on embedded interfaces."
        ),
        source="configuration/interfaces/wireguard.rst",
    ),
    Chunk(
        heading="Chocolate Cake",
        chunk_type="prose",
        text=(
            "To bake a chocolate cake, preheat the oven to 350 degrees. "
            "Mix flour, sugar, cocoa powder, baking soda, and eggs in a "
            "large bowl. Pour the batter into a greased baking pan."
        ),
        source="recipes/chocolate-cake.rst",
    ),
    Chunk(
        heading="Astronomy",
        chunk_type="prose",
        text=(
            "The Andromeda galaxy is the nearest large galaxy to the Milky "
            "Way. It is approximately 2.5 million light-years from Earth "
            "and is visible to the naked eye on moonless nights."
        ),
        source="science/astronomy.rst",
    ),
]


class TestAddAndRetrieve:
    """Tests for ChromaStore.add() and query()."""

    @requires_ollama
    def test_add_and_query_top1(self):
        store = ChromaStore(db_path=None, collection="test_add_query")
        store.add(SAMPLE_CHUNKS)
        results = store.query("VPN tunnel encrypted network", top_k=1)
        assert len(results) == 1
        assert "WireGuard" in results[0]["text"]

    @requires_ollama
    def test_query_returns_metadata(self):
        store = ChromaStore(db_path=None, collection="test_meta")
        store.add(SAMPLE_CHUNKS)
        results = store.query("VPN tunnel encrypted network", top_k=1)
        meta = results[0]["metadata"]
        assert meta["source_file"] == "configuration/interfaces/wireguard.rst"
        assert meta["heading_path"] == "WireGuard"
        assert meta["chunk_type"] == "prose"
        assert meta["embedding_model"] == "nomic-embed-text"

    @requires_ollama
    def test_query_returns_distance(self):
        store = ChromaStore(db_path=None, collection="test_dist")
        store.add(SAMPLE_CHUNKS)
        results = store.query("chocolate baking recipe", top_k=1)
        assert "distance" in results[0]
        assert isinstance(results[0]["distance"], float)


# ---------------------------------------------------------------------------
# 4.3 — Idempotent upsert
# ---------------------------------------------------------------------------


class TestIdempotentUpsert:
    """Adding the same chunks twice must not create duplicates."""

    @requires_ollama
    def test_double_add_same_count(self):
        store = ChromaStore(db_path=None, collection="test_idempotent")
        store.add(SAMPLE_CHUNKS)
        count_after_first = store._collection.count()
        store.add(SAMPLE_CHUNKS)
        count_after_second = store._collection.count()
        assert count_after_first == count_after_second == len(SAMPLE_CHUNKS)


# ---------------------------------------------------------------------------
# 4.4 — Worst match (farthest result)
# ---------------------------------------------------------------------------


class TestWorstMatch:
    """Tests for query(worst=True) returning the farthest result."""

    @requires_ollama
    def test_worst_match_returns_farthest(self):
        store = ChromaStore(db_path=None, collection="test_worst")
        store.add(SAMPLE_CHUNKS)
        best = store.query("VPN tunnel encrypted network", top_k=1)
        worst = store.query("VPN tunnel encrypted network", top_k=1, worst=True)
        assert worst[0]["text"] != best[0]["text"]
        assert worst[0]["distance"] >= best[0]["distance"]


# ---------------------------------------------------------------------------
# 4.5 — Rebuild collection
# ---------------------------------------------------------------------------


class TestRebuild:
    """Tests for rebuild=True wiping the collection."""

    @requires_ollama
    def test_rebuild_empties_collection(self):
        store = ChromaStore(db_path=None, collection="test_rebuild")
        store.add(SAMPLE_CHUNKS)
        assert store._collection.count() == len(SAMPLE_CHUNKS)

        store2 = ChromaStore(db_path=None, collection="test_rebuild", rebuild=True)
        assert store2._collection.count() == 0


# ---------------------------------------------------------------------------
# 4.6 — Oversized chunk splitting for embedding
# ---------------------------------------------------------------------------


class TestOversizedChunkSplitting:
    """Chunks exceeding max_embed_chars are split before embedding."""

    @requires_ollama
    def test_oversized_chunk_produces_multiple_vectors(self):
        store = ChromaStore(
            db_path=None, collection="test_oversized", max_embed_chars=200
        )
        big_chunk = Chunk(
            heading="Big",
            chunk_type="prose",
            text=(
                "This is a paragraph about networking. " * 30
                + "\n\n"
                + "This is a paragraph about security. " * 30
            ),
            source="big.rst",
        )
        store.add([big_chunk])
        count = store._collection.count()
        assert count > 1, f"Expected split into multiple vectors, got {count}"

    @requires_ollama
    def test_oversized_vectors_share_content_hash(self):
        store = ChromaStore(
            db_path=None, collection="test_oversized_hash", max_embed_chars=200
        )
        big_chunk = Chunk(
            heading="Big",
            chunk_type="prose",
            text=(
                "This is a paragraph about networking. " * 30
                + "\n\n"
                + "This is a paragraph about security. " * 30
            ),
            source="big.rst",
        )
        store.add([big_chunk])
        all_items = store._collection.get(include=["metadatas"])
        hashes = {m["content_hash"] for m in all_items["metadatas"]}
        assert len(hashes) == 1, f"Expected one content_hash, got {hashes}"
