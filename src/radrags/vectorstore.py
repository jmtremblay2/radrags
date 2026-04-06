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

    @staticmethod
    def _content_hash(text: str) -> str:
        """Return the SHA-256 hex digest of *text*.

        Used as the ChromaDB document ID so that identical text always
        maps to the same vector, making upserts idempotent.

        Args:
            text: The text to hash.

        Returns:
            64-character hex string.
        """
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def add(self, chunks: list[Chunk]) -> None:
        """Embed and upsert *chunks* into the collection.

        Each chunk is identified by ``sha256(text)``.  Re-adding the
        same chunk is a no-op (idempotent upsert).

        Args:
            chunks: List of ``Chunk`` objects to store.

        Example:
            ```python
            from radrags.chunker import Chunk
            from radrags.vectorstore import ChromaStore

            store = ChromaStore(db_path=None, collection="demo")
            store.add([
                Chunk("WireGuard", "prose",
                      "WireGuard is a fast VPN.",
                      "interfaces/wireguard.rst"),
            ])
            ```
        """
        ids: list[str] = []
        docs: list[str] = []
        metas: list[dict[str, Any]] = []
        embeds: list[list[float]] = []

        for chunk in chunks:
            content_hash = self._content_hash(chunk.text)
            embedding = self.embed(chunk.text)

            ids.append(content_hash)
            docs.append(chunk.text)
            metas.append(
                {
                    "source_file": chunk.source,
                    "heading_path": chunk.heading,
                    "chunk_type": chunk.chunk_type,
                    "token_count_estimate": max(1, len(chunk.text) // 4),
                    "content_hash": content_hash,
                    "embedding_model": self.embedding_model,
                }
            )
            embeds.append(embedding)

        if ids:
            self._collection.upsert(
                ids=ids, documents=docs, metadatas=metas, embeddings=embeds
            )

    def query(self, text: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Query the collection for chunks similar to *text*.

        Args:
            text: The query text to embed and search for.
            top_k: Number of top results to return.

        Returns:
            List of result dicts, each containing ``"text"``,
            ``"metadata"``, and ``"distance"`` keys, ordered by
            ascending distance (most similar first).

        Example:
            ```python
            store = ChromaStore(db_path=None, collection="demo")
            # ... add chunks first ...
            results = store.query("VPN tunnel", top_k=3)
            for r in results:
                print(r["distance"], r["text"][:60])
            ```
        """
        query_embedding = self.embed(text)
        raw = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

        results: list[dict[str, Any]] = []
        if raw["documents"] and raw["documents"][0]:
            for i, doc in enumerate(raw["documents"][0]):
                results.append(
                    {
                        "text": doc,
                        "metadata": raw["metadatas"][0][i] if raw["metadatas"] else {},
                        "distance": raw["distances"][0][i] if raw["distances"] else 0.0,
                    }
                )
        return results
