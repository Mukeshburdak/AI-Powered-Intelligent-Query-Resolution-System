from dotenv import load_dotenv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

from sqlalchemy import select
from backend.database.connection import SessionLocal
from backend.database.models import WhatsAppProcessedMessage
from backend.api.routes_whatsapp import (
    register_whatsapp_message,
    get_whatsapp_retry_payload,
)

def test_retry_payload_retrieval():
    message_id = "test_payload_retrieval_001"

    payload = {
        "type": "text",
        "sender": "919999999999",
        "user_id": 1,
        "question": "Test recovery question",
    }

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
    finally:
        db.close()

    registered = register_whatsapp_message(
        message_id,
        retry_payload=payload,
    )

    assert registered is True
    print("Encrypted payload registration: PASSED")

    retrieved = get_whatsapp_retry_payload(message_id)

    assert retrieved == payload
    print("Payload decryption and retrieval: PASSED")

    db = SessionLocal()

    try:
        record = db.execute(
            select(WhatsAppProcessedMessage).where(
                WhatsAppProcessedMessage.message_id == message_id
            )
        ).scalar_one()

        assert payload["question"] not in record.retry_payload
        print("Sensitive data encryption: PASSED")

    finally:
        db.close()


if __name__ == "__main__":
    test_retry_payload_retrieval()
    print("\nALL RETRY PAYLOAD RETRIEVAL TESTS PASSED.")