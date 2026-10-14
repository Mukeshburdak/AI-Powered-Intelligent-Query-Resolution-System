from src.query_understanding import understand_query
from src.clarification import needs_clarification, generate_clarification
from src.answer_generator import generate_answer


def process_query(query, retriever, embedding_model):

    # 1. Understand query
    query_data = understand_query(query)

    if not query_data["valid"]:
        return "Please enter a valid question."

    # 2. Check clarification
    if needs_clarification(query):
        return generate_clarification(query)

    # 3. Create query embedding
    query_embedding = embedding_model.encode(
        [query]
    )[0]

    # 4. Retrieve relevant information
    documents = retriever.search(query_embedding)

    # 5. Generate answer
    answer = generate_answer(
        query,
        documents
    )

    return answer
