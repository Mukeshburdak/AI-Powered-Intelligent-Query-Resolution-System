import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env", override=False)

import uuid

from backend.database.connection import SessionLocal
from backend.database.models import WhatsAppProcessedMessage
from backend.api.routes_whatsapp import update_whatsapp_message_status
def test_message_status_tracking():

    db = SessionLocal()
    message_id = f"status-test-{uuid.uuid4().hex}"

    try:
        record = WhatsAppProcessedMessage(
            message_id=message_id,
            status="received",
        )

        db.add(record)
        db.commit()

        print("\n========== MESSAGE STATUS TEST ==========")

        print("Initial status: received")

        update_whatsapp_message_status(
            message_id,
            "processing",
        )

        db.expire_all()
        record = db.query(WhatsAppProcessedMessage).filter_by(
            message_id=message_id
        ).first()

        assert record.status == "processing"
        print("Processing status: PASSED")

        update_whatsapp_message_status(
            message_id,
            "processed",
        )

        db.expire_all()
        record = db.query(WhatsAppProcessedMessage).filter_by(
            message_id=message_id
        ).first()

        assert record.status == "processed"
        print("Processed status: PASSED")

        update_whatsapp_message_status(
            message_id,
            "failed",
        )

        db.expire_all()
        record = db.query(WhatsAppProcessedMessage).filter_by(
            message_id=message_id
        ).first()

        assert record.status == "failed"
        print("Failed status: PASSED")

        print("\nSUCCESS: Message status tracking passed.")

    finally:
        db.query(WhatsAppProcessedMessage).filter_by(
            message_id=message_id
        ).delete()

        db.commit()
        db.close()


if __name__ == "__main__":
    test_message_status_tracking()