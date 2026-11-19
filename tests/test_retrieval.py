
from unittest.mock import patch

from backend.agents.retrieval_agent import RetrievalAgent


TEST_USER_ID = 42


def test_retrieval_filters_low_similarity(monkeypatch):
    monkeypatch.setenv("RETRIEVAL_MIN_SCORE", "0.30")
    agent = RetrievalAgent()

    fake_results = [
        {
            "source": "sample.txt",
            "chunk_id": "sample_0000",
            "text": "Unrelated document passage.",
            "score": 0.0413,
        },
        {
            "source": "sample.txt",
            "chunk_id": "sample_0001",
            "text": "Relevant document passage.",
            "score": 0.7356,
        },
    ]

    with patch(
        "backend.agents.retrieval_agent.vector_store.search",
        return_value=fake_results,
    ) as mock_search:

        results = agent.retrieve(
            "How does retrieval work?",
            user_id=TEST_USER_ID,
        )

    mock_search.assert_called_once_with(
        "How does retrieval work?",
        top_k=3,
        user_id=TEST_USER_ID,
    )

    assert len(results) == 1
    assert results[0]["chunk_id"] == "sample_0001"
    assert results[0]["score"] == 0.7356


def test_retrieval_returns_empty_when_all_scores_are_low(
    monkeypatch,
):
    monkeypatch.setenv("RETRIEVAL_MIN_SCORE", "0.30")
    agent = RetrievalAgent()

    with patch(
        "backend.agents.retrieval_agent.vector_store.search",
        return_value=[
            {
                "source": "sample.txt",
                "chunk_id": "sample_0000",
                "text": "Weak match.",
                "score": 0.0413,
            }
        ],
    ) as mock_search:

        results = agent.retrieve(
            "What is the capital of Japan?",
            user_id=TEST_USER_ID,
        )

    mock_search.assert_called_once_with(
        "What is the capital of Japan?",
        top_k=3,
        user_id=TEST_USER_ID,
    )

    assert results == []


def test_retrieval_handles_empty_question():
    agent = RetrievalAgent()

    with patch(
        "backend.agents.retrieval_agent.vector_store.search"
    ) as mock_search:

        assert agent.retrieve(
            "   ",
            user_id=TEST_USER_ID,
        ) == []

    mock_search.assert_not_called()
