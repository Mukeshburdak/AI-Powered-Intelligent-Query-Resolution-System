
import numpy as np
import pytest

from types import SimpleNamespace

from backend.embeddings import embedding_service


class FakeEmbeddingClient:
    class Models:
        def embed_content(self, model, contents, config):
            if isinstance(contents, str):
                texts = [contents]
            else:
                texts = contents

            embeddings = []

            for _ in texts:
                vector = np.zeros(768, dtype=np.float32)
                vector[0] = 3.0
                vector[1] = 4.0

                embeddings.append(
                    SimpleNamespace(values=vector.tolist())
                )

            return SimpleNamespace(embeddings=embeddings)

    def __init__(self):
        self.models = self.Models()


@pytest.fixture
def mock_gemini(monkeypatch):
    monkeypatch.setattr(
        embedding_service,
        "get_embedding_client",
        lambda: FakeEmbeddingClient(),
    )


def test_embeddings_return_normalized_vectors(mock_gemini):
    service = embedding_service.EmbeddingService()

    vectors = service.embed_texts([
        "The system resolves user queries.",
        "Documents contain useful information.",
    ])

    assert isinstance(vectors, np.ndarray)
    assert vectors.shape == (2, 768)
    assert vectors.dtype == np.float32
    assert np.allclose(
        np.linalg.norm(vectors, axis=1),
        1.0,
        atol=1e-5,
    )


def test_query_embedding_returns_single_vector(mock_gemini):
    service = embedding_service.EmbeddingService()

    vector = service.embed_query(
        "How does query resolution work?"
    )

    assert isinstance(vector, np.ndarray)
    assert vector.shape == (1, 768)
    assert vector.dtype == np.float32
    assert np.allclose(
        np.linalg.norm(vector),
        1.0,
        atol=1e-5,
    )


def test_empty_text_list_returns_empty_vectors():
    service = embedding_service.EmbeddingService()

    vectors = service.embed_texts([])

    assert isinstance(vectors, np.ndarray)
    assert vectors.shape == (0, 768)
    assert vectors.dtype == np.float32


def test_empty_query_is_rejected():
    service = embedding_service.EmbeddingService()

    with pytest.raises(ValueError):
        service.embed_query("   ")
