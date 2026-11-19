
import numpy as np

from backend.embeddings.embedding_service import EmbeddingService


def test_embeddings_return_normalized_vectors():
    service = EmbeddingService()

    vectors = service.embed_texts([
        "The system resolves user queries.",
        "Documents contain useful information.",
    ])

    assert isinstance(vectors, np.ndarray)
    assert vectors.shape == (2, 384)
    assert vectors.dtype == np.float32
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-5)


def test_query_embedding_returns_single_vector():
    service = EmbeddingService()

    vector = service.embed_query("How does query resolution work?")

    assert isinstance(vector, np.ndarray)
    assert vector.shape == (1, 384)
    assert vector.dtype == np.float32
    assert np.allclose(np.linalg.norm(vector), 1.0, atol=1e-5)


def test_empty_text_list_returns_empty_vectors():
    service = EmbeddingService()

    vectors = service.embed_texts([])

    assert isinstance(vectors, np.ndarray)
    assert vectors.shape == (0, 384)


def test_empty_query_is_rejected():
    import pytest

    service = EmbeddingService()

    with pytest.raises(ValueError):
        service.embed_query("   ")
