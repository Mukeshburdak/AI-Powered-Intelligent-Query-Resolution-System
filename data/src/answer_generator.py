def generate_answer(query, retrieved_documents):

    if not retrieved_documents:
        return "I could not find relevant information."

    context = "\n\n".join(retrieved_documents)

    return (
        f"Based on the available information:\n\n"
        f"{context}"
    )
