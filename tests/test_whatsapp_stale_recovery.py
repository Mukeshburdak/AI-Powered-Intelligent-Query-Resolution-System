
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env", override=False)

from backend.database.connection import SessionLocal
from backend.database.models import WhatsAppProcessedMessage
from backend.api.routes_whatsapp import recover_stale_whatsapp_messages


def test_stale_message_recovery():
    db = SessionLocal()

    message_id = "wamid.test_stale_recovery_001"

    try:
        db.query(WhatsAppProcessedMessage).filter(
            WhatsAppProcessedMessage.message_id == message_id
        ).delete()
        db.commit()

        stale_time = datetime.now(timezone.utc) - timedelta(minutes=20)

        record = WhatsAppProcessedMessage(
            message_id=message_id,
            status="processing",
            retry_count=0,
            processing_started_at=stale_time,
        )

        db.add(record)
        db.commit()

        recovered = recover_stale_whatsapp_messages(
            stale_after_minutes=15
        )

        assert recovered >= 1

        db.refresh(record)

        assert record.status == "failed"
        assert record.retry_count == 1
        assert record.processing_started_at is None
        assert record.last_error == "Processing interrupted or timed out."

        print("Stale message detection: PASSED")
        print("Status update to failed: PASSED")
        print("Retry counter increment: PASSED")
        print("Processing timestamp cleared: PASSED")

    finally:
        db.query(WhatsAppProcessedMessage).filter(
            WhatsAppProcessedMessage.message_id == message_id
        ).delete()
        db.commit()
        db.close()


if __name__ == "__main__":
    test_stale_message_recovery()
    print("\nALL STALE RECOVERY TESTS PASSED.")
