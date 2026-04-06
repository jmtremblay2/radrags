"""Vector store backed by ChromaDB with Ollama embeddings.

Provides the ``ChromaStore`` class for embedding, storing, and querying
document chunks using ChromaDB as the vector database and Ollama for
embedding generation.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import chromadb
from ollama import Client
from ollama._types import ResponseError

from radrags.chunker import Chunk

DEFAULT_DB_PATH = "./chroma_db"
DEFAULT_COLLECTION = "radrags"
DEFAULT_EMBEDDING_MODEL = "nomic-embed-text"
DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_MAX_EMBED_CHARS = 6000


class ChromaStore:
    """ChromaDB-backed vector store with Ollama embeddings.

    Wraps a ChromaDB collection and an Ollama embedding client.
    Chunks are embedded automatically on ``add()`` and queries
    are embedded on the fly in ``query()``.

    Args:
        db_path: Filesystem path for the persistent ChromaDB database.
            Pass ``None`` to use an ephemeral in-memory client.
        collection: Name of the ChromaDB collection.
        embedding_model: Ollama model used for embeddings.
        ollama_host: URL of the Ollama server.
        rebuild: When ``True``, delete the collection before
            creating it, discarding all existing vectors.
        max_embed_chars: Maximum characters per text sent to the
            embedding model.  Longer texts are split automatically.

    Example:
        ```python
        from radrags.vectorstore import ChromaStore

        store = ChromaStore(collection="my_docs")
        vec = store.embed("hello world")
        print(len(vec))  # 768
        ```
    """

    def __init__(
        self,
        db_path: str | None = DEFAULT_DB_PATH,
        collection: str = DEFAULT_COLLECTION,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        ollama_host: str = DEFAULT_OLLAMA_HOST,
        rebuild: bool = False,
        max_embed_chars: int = DEFAULT_MAX_EMBED_CHARS,
    ) -> None:
        self.embedding_model = embedding_model
        self.max_embed_chars = max_embed_chars
        self._ollama = Client(host=ollama_host)

        if db_path is None:
            self._chroma = chromadb.Client()
        else:
            self._chroma = chromadb.PersistentClient(path=db_path)

        if rebuild:
            try:
                self._chroma.delete_collection(collection)
            except Exception:
                pass

        self._collection = self._chroma.get_or_create_collection(name=collection)

    def embed(self, text: str) -> list[float]:
        """Compute an embedding vector for *text* via Ollama.

        Args:
            text: The text to embed.

        Returns:
            List of floats representing the embedding vector
            (768 dimensions for ``nomic-embed-text``).

        Example:
            ```python
            store = ChromaStore(collection="demo")
            vec = store.embed("WireGuard VPN tunnel")
            print(len(vec))  # 768
            ```
        """
        data: Any = self._ollama.embeddings(model=self.embedding_model, prompt=text)
        embedding = data.get("embedding")
        if not isinstance(embedding, list) or not embedding:
            raise RuntimeError("Ollama response did not include a valid embedding")
        return [float(v) for v in embedding]
