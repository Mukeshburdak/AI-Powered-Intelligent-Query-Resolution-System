
from backend.retrieval.vector_store import vector_store


def main():
    private_query = "NOVA-5821"

    # User 3 attempts to access User 4's private information.
    user3_results = vector_store.search(
        private_query,
        top_k=10,
        user_id=3,
    )

    # User 4 searches for their own private information.
    user4_results = vector_store.search(
        private_query,
        top_k=10,
        user_id=4,
    )

    print("\n========== CROSS-USER SECURITY TEST ==========")

    print("\nUser 3 searching for User 4's private code:")
    print("Results:", len(user3_results))

    for result in user3_results:
        print("Owner:", result.get("user_id"))
        print("Source:", result.get("source"))
        print("Text:", result.get("text")[:200])

    print("\nUser 4 searching for their own private code:")
    print("Results:", len(user4_results))

    for result in user4_results:
        print("Owner:", result.get("user_id"))
        print("Source:", result.get("source"))
        print("Text:", result.get("text")[:200])

    assert all(
        r.get("user_id") == 3 for r in user3_results
    )

    assert all(
        r.get("user_id") == 4 for r in user4_results
    )

    assert not any(
        "NOVA-5821" in r.get("text", "")
        for r in user3_results
    ), "SECURITY FAILURE: User 3 accessed User 4's private code!"

    assert any(
        "NOVA-5821" in r.get("text", "")
        for r in user4_results
    ), "User 4 could not retrieve their own private code."

    print("\nSUCCESS: Cross-user isolation test passed.")


if __name__ == "__main__":
    main()
