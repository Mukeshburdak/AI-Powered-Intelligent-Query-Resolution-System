
import uuid
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env", override=False)

from backend.database.connection import SessionLocal
from backend.database.models import WhatsAppProcessedMessage
from backend.api.routes_whatsapp import update_whatsapp_message_status


def test_failure_tracking():

    db = SessionLocal()
    message_id = f"failure-test-{uuid.uuid4().hex}"

    try:
        db.add(
            WhatsAppProcessedMessage(
                message_id=message_id,
                status="received",
            )
        )
        db.commit()

        print("\n========== FAILURE TRACKING TEST ==========")

        # Simulate a processing failure.
        update_whatsapp_message_status(
            message_id,
            "failed",
            error="Simulated processing failure.",
            increment_retry=True,
        )

        db.expire_all()

        record = db.query(WhatsAppProcessedMessage).filter_by(
            message_id=message_id
        ).first()

        assert record.status == "failed"
        assert record.retry_count == 1
        assert record.last_error == "Simulated processing failure."

        print("Failure status: PASSED")
        print("Retry count:", record.retry_count)
        print("Error recording: PASSED")

        # Simulate a successful subsequent processing attempt.
        update_whatsapp_message_status(
            message_id,
            "processed",
        )

        db.expire_all()

        record = db.query(WhatsAppProcessedMessage).filter_by(
            message_id=message_id
        ).first()

        assert record.status == "processed"
        assert record.retry_count == 1
        assert record.last_error is None

        print("Recovery status: PASSED")
        print("Previous error cleared: PASSED")
        print("Retry count preserved:", record.retry_count)

        print("\nSUCCESS: Failure tracking passed.")

    finally:
        db.query(WhatsAppProcessedMessage).filter_by(
            message_id=message_id
        ).delete()
        db.commit()
        db.close()


if __name__ == "__main__":
    test_failure_tracking()
