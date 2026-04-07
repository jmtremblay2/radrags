#!/usr/bin/env python3
"""Index VyOS 1.4.3 docs into ChromaDB and query them.

Usage:
    # Build the index (skips if already populated):
    uv run python examples/vyos_index.py --build-index

    # Query top 3 best matches (default):
    uv run python examples/vyos_index.py set up wireguard interface

    # Query top 5:
    uv run python examples/vyos_index.py --top 5 set up wireguard interface

    # Query worst 3 matches:
    uv run python examples/vyos_index.py --top 3 --worst set up wireguard interface

    # Build + query in one go:
    uv run python examples/vyos_index.py --build-index --top 5 set up wireguard interface
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from radrags.chunker import chunk_docs
from radrags.vectorstore import ChromaStore

DB_PATH = "chroma_db"
COLLECTION = "vyos-1.4.3"
DOCS_ROOT = Path("vendor/vyos-documentation/docs")


BATCH_SIZE = 20


def build_index(store: ChromaStore) -> None:
    if not DOCS_ROOT.exists():
        print(
            f"ERROR: {DOCS_ROOT} not found. Run ./scripts/clone_vyos_docs.sh first.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Chunking RST files under {DOCS_ROOT} ...")
    raw_chunks = chunk_docs(DOCS_ROOT)
    seen: set[str] = set()
    chunks = []
    for c in raw_chunks:
        if c.text not in seen:
            seen.add(c.text)
            chunks.append(c)
    print(f"  {len(raw_chunks)} chunks extracted, {len(chunks)} unique by text.")

    # Filter out chunks already in the collection by content-hash ID.
    candidate_ids = [hashlib.sha256(c.text.encode("utf-8")).hexdigest() for c in chunks]
    existing = set(store._collection.get(ids=candidate_ids, include=[])["ids"])
    new_chunks = [c for c, cid in zip(chunks, candidate_ids) if cid not in existing]

    if not new_chunks:
        print(f"  All chunks already indexed ({store._collection.count()} vectors).")
        return

    total = len(new_chunks)
    print(f"  {total} new chunks to embed ({len(existing)} already in DB).")

    print("Embedding and upserting into ChromaDB ...")
    for i in range(0, total, BATCH_SIZE):
        batch = new_chunks[i : i + BATCH_SIZE]
        store.add(batch)
        done = min(i + BATCH_SIZE, total)
        print(f"  [{done}/{total}] {done * 100 // total}%", flush=True)

    print(f"  Done. Collection now has {store._collection.count()} vectors.")


def run_query(store: ChromaStore, query: str, top_k: int, worst: bool) -> None:
    if store._collection.count() == 0:
        print("ERROR: Index is empty. Run with --build-index first.", file=sys.stderr)
        sys.exit(1)

    label = "WORST" if worst else "TOP"
    print(f"\n{label} {top_k} results for: {query!r}\n")

    results = store.query(query, top_k=top_k, worst=worst)
    for i, r in enumerate(results, 1):
        meta = r["metadata"]
        print(f"--- [{i}] distance={r['distance']:.4f} ---")
        print(f"  source : {meta.get('source_file', '?')}")
        print(f"  heading: {meta.get('heading_path', '?')}")
        print(f"  type   : {meta.get('chunk_type', '?')}")
        print(f"  text   : {r['text'][:200]}{'...' if len(r['text']) > 200 else ''}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Index VyOS 1.4.3 docs and query via ChromaDB + Ollama."
    )
    parser.add_argument(
        "--build-index",
        action="store_true",
        help="Build the vector index from VyOS docs (skips if already built).",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=3,
        metavar="K",
        help="Number of results to return (default: 3).",
    )
    parser.add_argument(
        "--worst",
        action="store_true",
        help="Return the worst (farthest) matches instead of the best.",
    )
    parser.add_argument(
        "query_words",
        nargs="*",
        help="Words of the query.",
    )

    args = parser.parse_args()

    if not args.build_index and not args.query_words:
        parser.print_help()
        sys.exit(1)

    store = ChromaStore(db_path=DB_PATH, collection=COLLECTION)

    if args.build_index:
        build_index(store)

    if args.query_words:
        query = " ".join(args.query_words)
        run_query(store, query, top_k=args.top, worst=args.worst)


if __name__ == "__main__":
    main()
