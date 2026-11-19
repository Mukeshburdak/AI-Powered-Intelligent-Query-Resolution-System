
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import importlib

import numpy as np

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env", override=False)

vector_store_module = importlib.import_module(
    "backend.retrieval.vector_store"
)


def test_duplicate_document_indexing():

    with TemporaryDirectory() as temp_dir:

        isolated_storage = Path(temp_dir)

        with (
            patch.object(
                vector_store_module,
                "STORAGE_DIR",
                isolated_storage,
            ),
            patch.object(
                vector_store_module,
                "INDEX_PATH",
                isolated_storage / "faiss.index",
            ),
            patch.object(
                vector_store_module,
                "METADATA_PATH",
                isolated_storage / "chunk_metadata.json",
            ),
        ):

            test_store = vector_store_module.FaissVectorStore()

            chunks = [
                {
                    "user_id": 98765,
                    "chunk_id": "wa_test_0000",
                    "source": "wa_test_document.txt",
                    "chunk_index": 0,
                    "text": "Test document content for FAISS idempotency.",
                }
            ]

            with patch.object(
                vector_store_module,
                "embed_texts",
                return_value=np.array(
                    [[1.0, 0.0, 0.0]],
                    dtype=np.float32,
                ),
            ):

                first_count = test_store.add_chunks(chunks)

                first_metadata_count = len(test_store.metadata)

                second_count = test_store.add_chunks(chunks)

                second_metadata_count = len(test_store.metadata)

            assert first_count == 1
            assert second_count == 1

            assert first_metadata_count == 1
            assert second_metadata_count == 1

            assert test_store.index.ntotal == 1

            print("First indexing: PASSED")
            print("Repeated indexing: PASSED")
            print("No duplicate metadata entries: PASSED")
            print("FAISS index count remains unchanged: PASSED")

    print("\nALL FAISS IDEMPOTENCY TESTS PASSED.")


if __name__ == "__main__":
    test_duplicate_document_indexing()
