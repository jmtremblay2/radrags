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
