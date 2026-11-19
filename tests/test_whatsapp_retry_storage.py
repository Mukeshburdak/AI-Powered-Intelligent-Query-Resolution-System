
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import select

import uuid

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env", override=False)

from backend.database.connection import SessionLocal
from backend.database.models import WhatsAppProcessedMessage
from backend.api.routes_whatsapp import (
    register_whatsapp_message,
    decrypt_retry_payload,
)


def test_retry_storage():

    message_id = f"retry-storage-{uuid.uuid4().hex}"

    original_payload = {
        "type": "text",
        "sender": "919876543210",
        "user_id": 3,
        "question": "What is the refund policy?",
    }

    print("\n========== RETRY STORAGE TEST ==========")

    try:
        # Register the message with encrypted payload.
        first_result = register_whatsapp_message(
            message_id,
            original_payload,
        )

        assert first_result is True

        print("Message registration: PASSED")

        db = SessionLocal()

        try:
            record = db.execute(
                select(WhatsAppProcessedMessage).where(
                    WhatsAppProcessedMessage.message_id == message_id
                )
            ).scalar_one()

            encrypted_payload = record.retry_payload

            assert encrypted_payload is not None
            assert "919876543210" not in encrypted_payload
            assert "refund policy" not in encrypted_payload

            print("Encrypted database storage: PASSED")
            print("Sensitive data protection: PASSED")

            # Verify that the original payload can be recovered.
            decrypted_payload = decrypt_retry_payload(
                encrypted_payload
            )

            assert decrypted_payload == original_payload

            print("Database payload decryption: PASSED")

        finally:
            db.close()

        # Verify duplicate protection.
        duplicate_result = register_whatsapp_message(
            message_id,
            original_payload,
        )

        assert duplicate_result is False

        print("Duplicate message rejection: PASSED")

        print("\nSUCCESS: Retry storage test passed.")

    finally:
        db = SessionLocal()

        try:
            db.query(WhatsAppProcessedMessage).filter_by(
                message_id=message_id
            ).delete()

            db.commit()

        finally:
            db.close()


if __name__ == "__main__":
    test_retry_storage()
