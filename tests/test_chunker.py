import pytest

from backend.ingestion.chunker import chunk_text


def test_chunk_text_returns_overlapping_chunks():
    chunks = chunk_text("abcdefghij", chunk_size=6, overlap=2)
    assert chunks == ["abcdef", "efghij"]


def test_chunk_text_returns_empty_list_for_empty_text():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_text_rejects_invalid_chunk_size():
    with pytest.raises(ValueError):
        chunk_text("hello", chunk_size=0, overlap=0)


def test_chunk_text_rejects_invalid_overlap():
    with pytest.raises(ValueError):
        chunk_text("hello", chunk_size=5, overlap=5)


def test_chunk_text_prefers_sentence_boundaries():
    text = (
        "The first sentence explains the system. "
        "The second sentence explains document ingestion. "
        "The third sentence explains retrieval."
    )

    chunks = chunk_text(text, chunk_size=55, overlap=10)

    assert len(chunks) > 1
    assert all(chunk.strip() for chunk in chunks)