"""FAISS integration placeholder. Do not persist uploaded confidential documents to Git."""
class FaissStore:
    def add_texts(self, texts: list[str], metadata: list[dict] | None = None):
        raise NotImplementedError("FAISS indexing is planned for the retrieval milestone.")

    def search(self, query: str, top_k: int = 5):
        raise NotImplementedError("Semantic retrieval is planned for the retrieval milestone.")
