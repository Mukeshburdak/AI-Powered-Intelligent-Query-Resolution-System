from pathlib import Path
from dotenv import load_dotenv
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env", override=False)

from backend.api.routes_whatsapp import retry_whatsapp_message
MESSAGE_ID = "wamid.test_retry_001"

TEXT_PAYLOAD = {
    "type": "text",
    "sender": "919999999999",
    "user_id": 3,
    "question": "Test retry question",
}


def test_retry_claim_rejected():
    with patch(
        "backend.api.routes_whatsapp.claim_whatsapp_message_for_retry",
        return_value=False,
    ):
        result = retry_whatsapp_message(MESSAGE_ID)

    assert result is False
    print("Duplicate retry claim rejection: PASSED")


def test_successful_text_retry():
    with (
        patch(
            "backend.api.routes_whatsapp.claim_whatsapp_message_for_retry",
            return_value=True,
        ),
        patch(
            "backend.api.routes_whatsapp.get_whatsapp_retry_payload",
            return_value=TEXT_PAYLOAD,
        ),
        patch(
            "backend.api.routes_whatsapp.get_linked_user_id",
            return_value=3,
        ),
        patch(
            "backend.api.routes_whatsapp.process_incoming_message",
            return_value=True,
        ) as mock_process,
        patch(
            "backend.api.routes_whatsapp.update_whatsapp_message_status"
        ) as mock_status,
    ):
        result = retry_whatsapp_message(MESSAGE_ID)

    assert result is True
    mock_process.assert_called_once_with(
        "919999999999",
        "Test retry question",
        3,
    )
    mock_status.assert_called_once_with(
        MESSAGE_ID,
        "processed",
    )

    print("Successful text retry: PASSED")


def test_retry_rejects_wrong_user():
    with (
        patch(
            "backend.api.routes_whatsapp.claim_whatsapp_message_for_retry",
            return_value=True,
        ),
        patch(
            "backend.api.routes_whatsapp.get_whatsapp_retry_payload",
            return_value=TEXT_PAYLOAD,
        ),
        patch(
            "backend.api.routes_whatsapp.get_linked_user_id",
            return_value=4,
        ),
        patch(
            "backend.api.routes_whatsapp.process_incoming_message"
        ) as mock_process,
        patch(
            "backend.api.routes_whatsapp.update_whatsapp_message_status"
        ) as mock_status,
    ):
        result = retry_whatsapp_message(MESSAGE_ID)

    assert result is False
    mock_process.assert_not_called()

    assert mock_status.call_args.kwargs["increment_retry"] is True

    print("Cross-user retry protection: PASSED")

def test_successful_document_retry():
    document_payload = {
        "type": "document",
        "sender": "919999999999",
        "user_id": 3,
        "media_id": "test_media_123",
        "filename": "test.pdf",
    }

    with (
        patch(
            "backend.api.routes_whatsapp.claim_whatsapp_message_for_retry",
            return_value=True,
        ),
        patch(
            "backend.api.routes_whatsapp.get_whatsapp_retry_payload",
            return_value=document_payload,
        ),
        patch(
            "backend.api.routes_whatsapp.get_linked_user_id",
            return_value=3,
        ),
        patch(
            "backend.api.routes_whatsapp.process_incoming_document",
            return_value=True,
        ) as mock_process,
        patch(
            "backend.api.routes_whatsapp.update_whatsapp_message_status"
        ) as mock_status,
    ):
        result = retry_whatsapp_message(MESSAGE_ID)

    assert result is True

    mock_process.assert_called_once_with(
        "919999999999",
        "test_media_123",
        "test.pdf",
        3,
        message_id=MESSAGE_ID,
    )

    mock_status.assert_called_once_with(
        MESSAGE_ID,
        "processed",
    )

    print("Successful document retry: PASSED")

def test_failed_text_retry():
    with (
        patch(
            "backend.api.routes_whatsapp.claim_whatsapp_message_for_retry",
            return_value=True,
        ),
        patch(
            "backend.api.routes_whatsapp.get_whatsapp_retry_payload",
            return_value=TEXT_PAYLOAD,
        ),
        patch(
            "backend.api.routes_whatsapp.get_linked_user_id",
            return_value=3,
        ),
        patch(
            "backend.api.routes_whatsapp.process_incoming_message",
            return_value=False,
        ),
        patch(
            "backend.api.routes_whatsapp.update_whatsapp_message_status"
        ) as mock_status,
    ):
        result = retry_whatsapp_message(MESSAGE_ID)

    assert result is False

    mock_status.assert_called_once_with(
        MESSAGE_ID,
        "failed",
        error="Retry processing or WhatsApp reply delivery failed.",
        increment_retry=True,
    )

    print("Failed retry status and counter: PASSED")

if __name__ == "__main__":
    test_retry_claim_rejected()
    test_successful_text_retry()
    test_successful_document_retry()
    test_retry_rejects_wrong_user()
    test_failed_text_retry()

    print("\nALL RETRY WORKER TESTS PASSED.")