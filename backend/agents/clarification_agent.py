class ClarificationAgent:
    def needs_clarification(self, question: str) -> bool:
        return len(question.strip()) < 4
