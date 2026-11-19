from dotenv import load_dotenv
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

from backend.api import routes_whatsapp

def test_success_returns_true():
    fake_result = {
        "status": "processed",
        "chunks": [{"text": "Test document content"}],
    }

    with patch.object(
        routes_whatsapp,
        "download_whatsapp_document",
        return_value=b"fake document",
    ), patch.object(
        routes_whatsapp,
        "ingest_file",
        return_value=fake_result,
    ), patch.object(
        routes_whatsapp.vector_store,
        "add_chunks",
        return_value=1,
    ), patch.object(
        routes_whatsapp,
        "send_whatsapp_message",
    ):
        result = routes_whatsapp.process_incoming_document(
            sender="919999999999",
            media_id="test_media",
            filename="test.txt",
            user_id=1,
        )

    assert result is True
    print("SUCCESS: Document processing returns True.")


def test_failure_returns_false():
    with patch.object(
        routes_whatsapp,
        "download_whatsapp_document",
        side_effect=Exception("Simulated download failure"),
    ), patch.object(
        routes_whatsapp,
        "send_whatsapp_message",
    ):
        result = routes_whatsapp.process_incoming_document(
            sender="919999999999",
            media_id="test_media",
            filename="test.txt",
            user_id=1,
        )

    assert result is False
    print("SUCCESS: Document processing returns False.")


if __name__ == "__main__":
    test_success_returns_true()
    test_failure_returns_false()
    print("\nALL DOCUMENT RETURN TESTS PASSED.")