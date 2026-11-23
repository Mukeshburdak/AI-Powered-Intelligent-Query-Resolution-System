
from unittest.mock import MagicMock, patch

from backend.agents.response_agent import ResponseAgent


def create_test_agent(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-api-key")

    mock_client = MagicMock()

    with patch(
        "backend.agents.response_agent.genai.Client",
        return_value=mock_client,
    ):
        agent = ResponseAgent()

    return agent, mock_client


def test_no_sources_returns_without_calling_model(monkeypatch):
    agent, mock_client = create_test_agent(monkeypatch)

    result = agent.respond(
        "What is in the document?",
        [],
    )

    mock_client.models.generate_content.assert_not_called()

    assert "couldn't find relevant information" in result["answer"].lower()
    assert result["sources"] == []
    assert result["confidence"] == 0.0
    assert result["provider"] == "Gemini"


def test_model_unavailable_returns_sources(monkeypatch):
    agent, mock_client = create_test_agent(monkeypatch)

    mock_client.models.generate_content.side_effect = RuntimeError(
        "Gemini is unavailable"
    )

    # Simulate Groq being unavailable too.
    def fail_groq(prompt, system_instruction):
        raise RuntimeError("Groq is unavailable")

    monkeypatch.setattr(agent, "_generate_groq", fail_groq)

    sources = [
        {
            "source": "sample.txt",
            "chunk_id": "sample_0000",
            "text": "The system uses a FAISS vector index.",
            "score": 0.8,
        }
    ]

    result = agent.respond(
        "How does retrieval work?",
        sources,
    )

    assert "could not generate an answer" in result["answer"].lower()
    assert result["sources"][0]["source"] == "sample.txt"
    assert result["sources"][0]["chunk_id"] == "sample_0000"
    assert result["confidence"] == 0.0
    assert result["provider"] == "Gemini"
    assert "Groq is unavailable" in result["generation_error"]
