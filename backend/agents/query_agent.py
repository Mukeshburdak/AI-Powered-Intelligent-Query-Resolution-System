
import re


class QueryAgent:
    """Prepare questions and identify their likely intent."""

    def prepare(self, question: str) -> str:
        return question.strip()

    def classify(self, question: str) -> dict:
        """Classify a question using lightweight, rule-based heuristics."""
        normalized = self.prepare(question)
        text = normalized.lower()

        if not text:
            return {
                "intent": "ambiguous",
                "question_type": "ambiguous",
                "needs_clarification": True,
            }

        comparative_patterns = [
            r"\bcompare\b",
            r"\bcomparison\b",
            r"\bdifference(?:s)? between\b",
            r"\bversus\b",
            r"\bvs\.?\b",
            r"\bwhich is better\b",
        ]

        procedural_patterns = [
            r"^\s*how do i\b",
            r"^\s*how can i\b",
            r"^\s*how to\b",
            r"^\s*what are the steps\b",
            r"^\s*explain how\b",
            r"^\s*procedure for\b",
        ]

        if any(re.search(pattern, text) for pattern in comparative_patterns):
            question_type = "comparative"
        elif any(re.search(pattern, text) for pattern in procedural_patterns):
            question_type = "procedural"
        elif (
            len(text.split()) < 3
            or text in {"help", "explain", "tell me more", "what about it"}
        ):
            question_type = "ambiguous"
        else:
            question_type = "factual"

        return {
            "intent": question_type,
            "question_type": question_type,
            "needs_clarification": question_type == "ambiguous",
        }
