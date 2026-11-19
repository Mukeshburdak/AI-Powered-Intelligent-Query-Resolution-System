
import os

from backend.retrieval.vector_store import vector_store


class RetrievalAgent:
    def __init__(self):
        try:
            self.min_score = float(
                os.getenv("RETRIEVAL_MIN_SCORE", "0.30")
            )
        except ValueError:
            self.min_score = 0.30

    def retrieve(
        self,
        question: str,
        user_id: int,
        document_id: str | None = None,
    ) -> list[dict]:
        """Retrieve relevant chunks from a user's selected document."""

        if not question or not question.strip():
            return []

        if user_id is None:
            raise ValueError(
                "A valid user_id is required for retrieval."
            )

        search_options = {
            "top_k": 3,
            "user_id": user_id,
        }

        if document_id is not None:
            search_options["source"] = document_id

        results = vector_store.search(
            question,
            **search_options,
        )

        relevant_results = []

        for result in results:
            score = float(result.get("score", 0.0))

            if score < self.min_score:
                continue

            relevant_results.append({
                "source": result["source"],
                "chunk_id": result["chunk_id"],
                "text": result["text"],
                "score": score,
            })

        return relevant_results
