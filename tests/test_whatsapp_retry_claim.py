from dotenv import load_dotenv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

from sqlalchemy import select
from backend.database.connection import SessionLocal
from backend.database.models import WhatsAppProcessedMessage
from backend.api.routes_whatsapp import claim_whatsapp_message_for_retry


def test_retry_claim():
    message_id = "test_retry_claim_001"
    db = SessionLocal()

    try:
        existing = db.execute(
            select(WhatsAppProcessedMessage).where(
                WhatsAppProcessedMessage.message_id == message_id
            )
        ).scalar_one_or_none()

        if existing:
            db.delete(existing)
            db.commit()

        db.add(
            WhatsAppProcessedMessage(
                message_id=message_id,
                status="failed",
                retry_count=0,
            )
        )
        db.commit()

    finally:
        db.close()

    # First worker should claim the message.
    first_claim = claim_whatsapp_message_for_retry(message_id)

    assert first_claim is True
    print("First worker claim: PASSED")

    # Second worker must not claim the same message.
    second_claim = claim_whatsapp_message_for_retry(message_id)

    assert second_claim is False
    print("Duplicate worker claim rejected: PASSED")

    db = SessionLocal()

    try:
        record = db.execute(
            select(WhatsAppProcessedMessage).where(
                WhatsAppProcessedMessage.message_id == message_id
            )
        ).scalar_one()

        assert record.status == "processing"
        assert record.processing_started_at is not None

        print("Database processing status: PASSED")

    finally:
        db.close()


if __name__ == "__main__":
    test_retry_claim()
    print("\nALL RETRY CLAIM TESTS PASSED.")