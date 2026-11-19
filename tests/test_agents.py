from backend.agents.clarification_agent import ClarificationAgent
from backend.agents.query_agent import QueryAgent

def test_query_agent_trims_whitespace():
    assert QueryAgent().prepare("  hello  ") == "hello"

def test_clarification_agent_flags_tiny_question():
    assert ClarificationAgent().needs_clarification(" ? ")
