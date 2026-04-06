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
        same chunk is a no-op (idempotent upsert).  Chunks whose text
        exceeds ``max_embed_chars`` are split at paragraph boundaries
        before embedding; all sub-vectors share the same
        ``content_hash`` in metadata.

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
            subchunks = self._split_for_embedding(chunk.text)

            for idx, subtext in enumerate(subchunks):
                pairs = self._embed_with_fallback(subtext)
                for final_text, final_embedding in pairs:
                    sub_id = (
                        self._content_hash(f"{content_hash}:{idx}:{final_text}")
                        if len(subchunks) > 1
                        else content_hash
                    )

                    ids.append(sub_id)
                    docs.append(final_text)
                    metas.append(
                        {
                            "source_file": chunk.source,
                            "heading_path": chunk.heading,
                            "chunk_type": chunk.chunk_type,
                            "token_count_estimate": max(1, len(final_text) // 4),
                            "content_hash": content_hash,
                            "embedding_model": self.embedding_model,
                        }
                    )
                    embeds.append(final_embedding)

        if ids:
            self._collection.upsert(
                ids=ids, documents=docs, metadatas=metas, embeddings=embeds
            )

    def _split_for_embedding(self, text: str, overlap_chars: int = 300) -> list[str]:
        """Split *text* into pieces that fit within ``max_embed_chars``.

        Prefers paragraph boundaries; falls back to fixed windowing
        with overlap when a single paragraph is too long.

        Args:
            text: The text to split.
            overlap_chars: Characters of shared context between pieces.

        Returns:
            List of text pieces, each at most ``max_embed_chars`` long.
        """
        text = text.strip()
        if not text:
            return []
        if len(text) <= self.max_embed_chars:
            return [text]

        parts: list[str] = []
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        current = ""
        for para in paragraphs:
            candidate = f"{current}\n\n{para}".strip() if current else para
            if len(candidate) <= self.max_embed_chars:
                current = candidate
                continue
            if current:
                parts.append(current)
                tail = current[-overlap_chars:] if overlap_chars > 0 else ""
                current = f"{tail}\n\n{para}".strip() if tail else para
            else:
                start = 0
                step = max(1, self.max_embed_chars - overlap_chars)
                while start < len(para):
                    piece = para[start : start + self.max_embed_chars].strip()
                    if piece:
                        parts.append(piece)
                    start += step
                current = ""
        if current:
            parts.append(current)
        return parts

    def _embed_with_fallback(
        self, text: str, min_chars: int = 500
    ) -> list[tuple[str, list[float]]]:
        """Embed *text*, splitting on context-length overflow.

        If the embedding model reports that the input exceeds its
        context window, the text is split in half and retried
        recursively.

        Args:
            text: The text to embed.
            min_chars: Minimum piece size before giving up.

        Returns:
            List of ``(text_piece, embedding)`` tuples.
        """
        text = text.strip()
        if not text:
            return []
        try:
            return [(text, self.embed(text))]
        except ResponseError as exc:
            message = str(exc).lower()
            if "input length exceeds the context length" not in message:
                raise
            if len(text) <= min_chars:
                raise RuntimeError(
                    f"Embedding overflow at minimum split size ({len(text)} chars)"
                ) from exc
            mid = len(text) // 2
            left = text[:mid].strip()
            right = text[mid:].strip()
            if not left or not right:
                raise RuntimeError(
                    "Unable to split oversized embedding text safely"
                ) from exc
            return self._embed_with_fallback(
                left, min_chars=min_chars
            ) + self._embed_with_fallback(right, min_chars=min_chars)

    def query(
        self, text: str, top_k: int = 5, worst: bool = False
    ) -> list[dict[str, Any]]:
        """Query the collection for chunks similar to *text*.

        Args:
            text: The query text to embed and search for.
            top_k: Number of top results to return.
            worst: When ``True``, return the *farthest* results
                instead of the closest.  Queries the full collection
                and returns the last *top_k* results by distance.

        Returns:
            List of result dicts, each containing ``"text"``,
            ``"metadata"``, and ``"distance"`` keys.  Ordered by
            ascending distance (most similar first) unless
            ``worst=True``, in which case ordered by descending
            distance (least similar first).

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

        if worst:
            n = self._collection.count()
            if n == 0:
                return []
            raw = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=n,
            )
        else:
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
                        "distance": (
                            raw["distances"][0][i] if raw["distances"] else 0.0
                        ),
                    }
                )

        if worst:
            results.sort(key=lambda r: r["distance"], reverse=True)
            return results[:top_k]
        return results
