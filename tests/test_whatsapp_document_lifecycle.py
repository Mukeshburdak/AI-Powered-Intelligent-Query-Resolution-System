from dotenv import load_dotenv
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

from backend.api import routes_whatsapp


def test_document_success_status():
    with patch.object(
        routes_whatsapp,
        "update_whatsapp_message_status",
    ) as mock_status, patch.object(
        routes_whatsapp,
        "process_incoming_document",
        return_value=True,
    ):
        routes_whatsapp.process_tracked_incoming_document(
            "test_msg_success",
            "919999999999",
            "media123",
            "test.pdf",
            1,
        )

    calls = [
        call.args[1]
        for call in mock_status.call_args_list
    ]

    assert calls == ["processing", "processed"]
    print("SUCCESS: Document marked as processed.")


def test_document_failure_status():
    with patch.object(
        routes_whatsapp,
        "update_whatsapp_message_status",
    ) as mock_status, patch.object(
        routes_whatsapp,
        "process_incoming_document",
        return_value=False,
    ):
        routes_whatsapp.process_tracked_incoming_document(
            "test_msg_failure",
            "919999999999",
            "media123",
            "test.pdf",
            1,
        )

    assert mock_status.call_count == 2

    failure_call = mock_status.call_args_list[1]

    assert failure_call.args[1] == "failed"
    assert failure_call.kwargs["increment_retry"] is True

    print("SUCCESS: Document failure recorded and retry count incremented.")


if __name__ == "__main__":
    test_document_success_status()
    test_document_failure_status()
    print("\nALL DOCUMENT LIFECYCLE TESTS PASSED.")