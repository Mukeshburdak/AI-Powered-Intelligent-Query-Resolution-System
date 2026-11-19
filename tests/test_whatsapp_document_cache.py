
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env", override=False)

def test_cached_document_reuse():

    with TemporaryDirectory() as temp_dir:

        user_id = 98765
        message_id = "wamid.test_cached_document_001"
        filename = "cached_test.txt"

        user_directory = Path(temp_dir) / str(user_id)
        user_directory.mkdir(parents=True)

        destination_name = (
            "wa_"
            + __import__("hashlib").sha256(
                message_id.encode("utf-8")
            ).hexdigest()[:24]
            + "_"
            + filename
        )

        cached_file = user_directory / destination_name
        cached_file.write_text(
            "This is a cached document for retry testing.",
            encoding="utf-8",
        )

        fake_chunks = [
            {
                "text": "This is a cached document for retry testing.",
                "metadata": {"source": filename},
            }
        ]

        with (
            patch(
                "backend.api.routes_whatsapp.SAMPLE_DOCUMENTS_DIR",
                Path(temp_dir),
            ),
            patch(
                "backend.api.routes_whatsapp.download_whatsapp_document"
            ) as download_mock,
            patch(
                "backend.api.routes_whatsapp.ingest_file",
                return_value={
                    "status": "processed",
                    "chunks": fake_chunks,
                },
            ) as ingest_mock,
            patch(
                "backend.api.routes_whatsapp.vector_store.add_chunks",
                return_value=1,
            ) as index_mock,
            patch(
                "backend.api.routes_whatsapp.send_whatsapp_message"
            ) as send_mock,
        ):

            from backend.api.routes_whatsapp import (
                process_incoming_document,
            )

            result = process_incoming_document(
                sender="15550000000",
                media_id="test_media_id",
                filename=filename,
                user_id=user_id,
                message_id=message_id,
            )

            assert result is True

            download_mock.assert_not_called()
            ingest_mock.assert_called_once()
            index_mock.assert_called_once()

            indexed_chunks = index_mock.call_args.args[0]
            assert indexed_chunks[0]["user_id"] == user_id

            send_mock.assert_called_once()

            print("Cached document reuse: PASSED")
            print("Meta download skipped: PASSED")
            print("Document ingestion: PASSED")
            print("FAISS indexing: PASSED")
            print("User isolation metadata: PASSED")
            print("WhatsApp confirmation: PASSED")


if __name__ == "__main__":
    test_cached_document_reuse()
    print("\nALL DOCUMENT CACHE TESTS PASSED.")
