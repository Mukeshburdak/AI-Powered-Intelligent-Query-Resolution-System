
import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_model = None


def get_embedding_model() -> SentenceTransformer:
    """Load the embedding model once and reuse it."""
    global _model

    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)

    return _model


def embed_texts(texts: list[str]) -> np.ndarray:
    """Convert multiple text chunks into normalized vectors."""
    if not texts:
        return np.empty((0, 384), dtype=np.float32)

    model = get_embedding_model()

    vectors = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    return np.asarray(vectors, dtype=np.float32)


def embed_query(query: str) -> np.ndarray:
    """Convert a user question into a normalized vector."""
    if not query or not query.strip():
        raise ValueError("Query must not be empty.")

    model = get_embedding_model()

    vector = model.encode(
        query.strip(),
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    return np.asarray(vector, dtype=np.float32).reshape(1, -1)


class EmbeddingService:
    """Class-based interface compatible with existing tests."""

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        return embed_texts(texts)

    def embed_query(self, query: str) -> np.ndarray:
        return embed_query(query)
