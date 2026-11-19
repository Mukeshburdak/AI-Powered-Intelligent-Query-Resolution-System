
from backend.retrieval.vector_store import vector_store

# Check how many document chunks belong to each user.
metadata = vector_store.metadata

print("\n========== USER DOCUMENT ISOLATION ==========")

for user_id in [1, 2, 3, 4]:
    user_chunks = [
        item for item in metadata
        if str(item.get("user_id")) == str(user_id)
    ]

    print(f"\nUser ID: {user_id}")
    print(f"Total chunks: {len(user_chunks)}")

    sources = sorted({
        item.get("source", "Unknown")
        for item in user_chunks
    })

    print("Documents:", sources)

print("\n=============================================")
