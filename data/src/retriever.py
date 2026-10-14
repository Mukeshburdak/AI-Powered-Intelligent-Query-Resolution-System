import faiss
import numpy as np


class Retriever:

    def __init__(self, embeddings, documents):
        self.documents = documents

        embeddings = np.array(embeddings).astype("float32")

        self.index = faiss.IndexFlatL2(
            embeddings.shape[1]
        )

        self.index.add(embeddings)

    def search(self, query_embedding, top_k=3):

        query_embedding = np.array(
            [query_embedding]
        ).astype("float32")

        distances, indices = self.index.search(
            query_embedding,
            top_k
        )

        results = [
            self.documents[i]
            for i in indices[0]
        ]

        return results
