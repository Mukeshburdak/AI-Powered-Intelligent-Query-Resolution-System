
import uuid
from pathlib import Path
from dotenv import load_dotenv
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env", override=False)

from backend.database.connection import SessionLocal
from backend.database.models import WhatsAppProcessedMessage
from backend.api import routes_whatsapp


def run_test(message_id, wrapper, expected_status, *args):
    db = SessionLocal()

    try:
        db.add(
            WhatsAppProcessedMessage(
                message_id=message_id,
                status="received",
            )
        )
        db.commit()

        wrapper(message_id, *args)

        db.expire_all()

        record = (
            db.query(WhatsAppProcessedMessage)
            .filter_by(message_id=message_id)
            .first()
        )

        assert record is not None
        assert record.status == expected_status, (
            f"Expected {expected_status}, got {record.status}"
        )

        print(f"{wrapper.__name__}: {expected_status} PASSED")

    finally:
        db.query(WhatsAppProcessedMessage).filter_by(
            message_id=message_id
        ).delete()
        db.commit()
        db.close()


def test_processing_wrappers():

    print("\n========== PROCESSING WRAPPER TEST ==========")

    test_cases = [
        (
            "text_success",
            routes_whatsapp.process_tracked_incoming_message,
            "processed",
            ("sender", "Test question", 3),
            True,
            "process_incoming_message",
        ),
        (
            "text_failure",
            routes_whatsapp.process_tracked_incoming_message,
            "failed",
            ("sender", "Test question", 3),
            False,
            "process_incoming_message",
        ),
        (
            "document_success",
            routes_whatsapp.process_tracked_incoming_document,
            "processed",
            ("sender", "media123", "test.pdf", 3),
            True,
            "process_incoming_document",
        ),
        (
            "document_failure",
            routes_whatsapp.process_tracked_incoming_document,
            "failed",
            ("sender", "media123", "test.pdf", 3),
            False,
            "process_incoming_document",
        ),
    ]

    for name, wrapper, expected, args, result, target in test_cases:

        message_id = f"wrapper-{name}-{uuid.uuid4().hex}"

        with patch.object(
            routes_whatsapp,
            target,
            return_value=result,
        ):
            run_test(
                message_id,
                wrapper,
                expected,
                *args,
            )

    print("\nSUCCESS: All processing wrapper tests passed.")


if __name__ == "__main__":
    test_processing_wrappers()
