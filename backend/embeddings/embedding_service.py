
import os

import numpy as np
from google import genai
from google.genai import types


MODEL_NAME = os.getenv(
    "GEMINI_EMBEDDING_MODEL",
    "gemini-embedding-001",
)

EMBEDDING_DIMENSION = 768
BATCH_SIZE = 50

_client = None


def get_embedding_client():
    """Create and reuse the Gemini API client."""
    global _client

    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is missing from environment."
            )

        _client = genai.Client(api_key=api_key)

    return _client


def _normalize(vectors) -> np.ndarray:
    """Convert vectors to normalized float32 arrays."""
    vectors = np.asarray(vectors, dtype=np.float32)

    if vectors.size == 0:
        return np.empty(
            (0, EMBEDDING_DIMENSION),
            dtype=np.float32,
        )

    norms = np.linalg.norm(vectors, axis=1, keepdims=True)

    return vectors / np.maximum(norms, 1e-12)


def embed_texts(texts: list[str]) -> np.ndarray:
    """Generate normalized document embeddings in batches."""
    if not texts:
        return np.empty(
            (0, EMBEDDING_DIMENSION),
            dtype=np.float32,
        )

    client = get_embedding_client()
    all_vectors = []

    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start:start + BATCH_SIZE]

        response = client.models.embed_content(
            model=MODEL_NAME,
            contents=batch,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=EMBEDDING_DIMENSION,
            ),
        )

        if (
            not response.embeddings
            or len(response.embeddings) != len(batch)
        ):
            raise RuntimeError(
                "Gemini returned an unexpected number of document embeddings."
            )

        all_vectors.extend(
            embedding.values
            for embedding in response.embeddings
        )

    return _normalize(all_vectors)


def embed_query(query: str) -> np.ndarray:
    """Generate one normalized query embedding."""
    if not query or not query.strip():
        raise ValueError("Query must not be empty.")

    client = get_embedding_client()

    response = client.models.embed_content(
        model=MODEL_NAME,
        contents=query.strip(),
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=EMBEDDING_DIMENSION,
        ),
    )

    if not response.embeddings:
        raise RuntimeError(
            "Gemini did not return a query embedding."
        )

    return _normalize([
        response.embeddings[0].values
    ])


class EmbeddingService:
    """Class-based interface used by the existing application."""

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        return embed_texts(texts)

    def embed_query(self, query: str) -> np.ndarray:
        return embed_query(query)
