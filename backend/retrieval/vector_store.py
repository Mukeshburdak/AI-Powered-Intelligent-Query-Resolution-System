
import json

import faiss
import numpy as np

from backend.embeddings.embedding_service import (
    embed_query,
    embed_texts,
)

from backend.config import STORAGE_DIR

INDEX_PATH = STORAGE_DIR / "faiss.index"
METADATA_PATH = STORAGE_DIR / "chunk_metadata.json"


class FaissVectorStore:
    """Persist document chunks and search by user ownership."""

    def __init__(self):
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)

        self.metadata = []
        self.index = None
        self._load()

    def _load(self):
        """Load the saved index and matching metadata."""

        if METADATA_PATH.exists():
            self.metadata = json.loads(
                METADATA_PATH.read_text(encoding="utf-8")
            )

        if INDEX_PATH.exists():
            self.index = faiss.read_index(str(INDEX_PATH))

            if self.index.ntotal != len(self.metadata):
                raise ValueError(
                    "FAISS index and metadata counts do not match."
                )

    def _save(self):
        """Persist the index and its metadata."""

        if self.index is not None:
            faiss.write_index(self.index, str(INDEX_PATH))

        METADATA_PATH.write_text(
            json.dumps(
                self.metadata,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _rebuild_index(self):
        """Rebuild the index using the current embedding model."""

        if not self.metadata:
            self.index = None
            return

        vectors = embed_texts(
            [item["text"] for item in self.metadata]
        )

        if (
            vectors.ndim != 2
            or vectors.shape[0] != len(self.metadata)
            or vectors.shape[1] == 0
        ):
            raise ValueError(
                "Invalid embeddings returned while rebuilding FAISS index."
            )

        vectors = np.ascontiguousarray(
            vectors,
            dtype=np.float32,
        )

        new_index = faiss.IndexFlatIP(vectors.shape[1])
        new_index.add(vectors)

        self.index = new_index
        self._save()

    def add_chunks(self, chunks: list[dict]) -> int:
        """Add chunks while preserving their user ownership."""

        valid_chunks = [
            {
                "user_id": int(chunk["user_id"]),
                "chunk_id": str(chunk["chunk_id"]),
                "source": str(chunk["source"]),
                "chunk_index": int(chunk["chunk_index"]),
                "text": str(chunk["text"]),
            }
            for chunk in chunks
            if chunk.get("text", "").strip()
            and chunk.get("user_id") is not None
        ]

        if not valid_chunks:
            return 0

        merged = {
            (
                item.get("user_id"),
                item["source"],
                item["chunk_id"],
            ): item
            for item in self.metadata
        }

        for chunk in valid_chunks:
            key = (
                chunk["user_id"],
                chunk["source"],
                chunk["chunk_id"],
            )
            merged[key] = chunk

        self.metadata = list(merged.values())

        self._rebuild_index()

        return len(valid_chunks)

    def search(
        self,
        query: str,
        top_k: int = 5,
        user_id: int | None = None,
        source: str | None = None,
    ) -> list[dict]:
        """Search chunks belonging to a user and optionally one document."""

        if top_k < 1:
            raise ValueError("top_k must be at least 1.")

        # Fail closed: never perform an unfiltered search.
        if user_id is None:
            raise ValueError(
                "user_id is required for document retrieval."
            )

        if not query or not query.strip():
            return []

        if self.index is None or self.index.ntotal == 0:
            return []

        query_vector = embed_query(query)

        if query_vector.ndim != 2 or query_vector.shape[0] != 1:
            raise ValueError(
                "Query embedding must contain exactly one vector."
            )

        # Automatically migrate an old index when dimensions differ.
        if self.index.d != query_vector.shape[1]:
            self._rebuild_index()

            if self.index is None or self.index.ntotal == 0:
                return []

        scores, positions = self.index.search(
            np.ascontiguousarray(
                query_vector,
                dtype=np.float32,
            ),
            self.index.ntotal,
        )

        results = []

        for score, position in zip(scores[0], positions[0]):
            if position < 0:
                continue

            metadata = self.metadata[int(position)]

            if metadata.get("user_id") != int(user_id):
                continue

            if source is not None and metadata.get("source") != source:
                continue

            results.append({
                **metadata,
                "score": float(score),
            })

            if len(results) >= top_k:
                break

        return results


# Shared vector store instance used by the application.
vector_store = FaissVectorStore()
