
from backend.retrieval.vector_store import vector_store


def main():
    query = "What information is available in the uploaded documents?"

    # Use an existing application user ID for this retrieval.
    user_id = 1

    results = vector_store.search(
        query,
        top_k=3,
        user_id=user_id,
    )

    print("\n========== RETRIEVAL DEMO ==========")

    if not results:
        print("No matching documents found for this user.")
        return

    for index, result in enumerate(results, start=1):
        print(f"\nResult {index}:")
        print(result)


if __name__ == "__main__":
    main()
