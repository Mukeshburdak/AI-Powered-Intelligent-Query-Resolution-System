import sys
import shutil
from datetime import datetime
from pathlib import Path

# Add project root to Python import path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import (
    ALLOWED_DOCUMENT_EXTENSIONS,
    SAMPLE_DOCUMENTS_DIR,
)
from backend.ingestion.ingestion_pipeline import ingest_file
from backend.retrieval.vector_store import vector_store


STORAGE_DIR = PROJECT_ROOT / "storage"

def main():
    print("Starting FAISS index rebuild...")

    # Step 1: Back up the existing index and metadata.
    backup_dir = STORAGE_DIR / "backups" / datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )
    backup_dir.mkdir(parents=True, exist_ok=True)

    for filename in ("faiss.index", "chunk_metadata.json"):
        source = STORAGE_DIR / filename

        if source.exists():
            shutil.copy2(source, backup_dir / filename)
            print(f"Backup created: {filename}")

    # Step 2: Find all user directories and process their files.
    all_chunks = []

    user_directories = [
        directory
        for directory in SAMPLE_DOCUMENTS_DIR.iterdir()
        if directory.is_dir() and directory.name.isdigit()
    ]

    for user_directory in user_directories:
        user_id = int(user_directory.name)

        for document in user_directory.iterdir():
            if (
                not document.is_file()
                or document.suffix.lower()
                not in ALLOWED_DOCUMENT_EXTENSIONS
            ):
                continue

            print(
                f"Processing {document.name} "
                f"for user {user_id}..."
            )

            result = ingest_file(document)

            chunks = [
                {
                    **chunk,
                    "user_id": user_id,
                }
                for chunk in result.get("chunks", [])
            ]

            all_chunks.extend(chunks)

            print(
                f"Created {len(chunks)} chunks "
                f"for user {user_id}."
            )

    # Step 3: Do not replace the old index if no documents
    # were successfully processed.
    if not all_chunks:
        raise RuntimeError(
            "No document chunks were created. "
            "The existing index has not been replaced."
        )

    # Step 4: Rebuild from verified user-owned documents.
    vector_store.metadata = []
    vector_store.index = None

    indexed_count = vector_store.add_chunks(all_chunks)

    print("\nFAISS rebuild completed successfully.")
    print(f"Total indexed chunks: {indexed_count}")
    print(f"Total user directories: {len(user_directories)}")
    print(f"Backup location: {backup_dir}")


if __name__ == "__main__":
    main()
