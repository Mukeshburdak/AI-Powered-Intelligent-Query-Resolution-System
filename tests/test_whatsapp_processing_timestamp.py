from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

from backend.database.connection import SessionLocal
from backend.database.models import WhatsAppProcessedMessage
from backend.api.routes_whatsapp import update_whatsapp_message_status

def test_processing_timestamp():
    message_id = "test_timestamp_001"
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
                status="received",
            )
        )
        db.commit()

        update_whatsapp_message_status(message_id, "processing")

        db.refresh(
            db.execute(
                select(WhatsAppProcessedMessage).where(
                    WhatsAppProcessedMessage.message_id == message_id
                )
            ).scalar_one()
        )

        record = db.execute(
            select(WhatsAppProcessedMessage).where(
                WhatsAppProcessedMessage.message_id == message_id
            )
        ).scalar_one()

        assert record.processing_started_at is not None
        print("Processing timestamp: PASSED")

        update_whatsapp_message_status(message_id, "processed")

        db.expire_all()

        record = db.execute(
            select(WhatsAppProcessedMessage).where(
                WhatsAppProcessedMessage.message_id == message_id
            )
        ).scalar_one()

        assert record.processing_started_at is None
        print("Timestamp cleared after completion: PASSED")

    finally:
        db.close()


if __name__ == "__main__":
    test_processing_timestamp()
    print("\nALL TIMESTAMP TESTS PASSED.")