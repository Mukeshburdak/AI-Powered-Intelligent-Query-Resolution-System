from pathlib import Path
from dotenv import load_dotenv

# Load project environment before importing backend modules.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=False)

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.connection import Base
from backend.database.models import WhatsAppProcessedMessage
import backend.api.routes_whatsapp as whatsapp
@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """Create an isolated temporary SQLite database."""

    database_path = tmp_path / "whatsapp_retry_test.db"

    test_engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )

    Base.metadata.create_all(bind=test_engine)

    TestSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )

    monkeypatch.setattr(
        whatsapp,
        "SessionLocal",
        TestSessionLocal,
    )

    yield TestSessionLocal

    test_engine.dispose()


def get_record(Session, message_id):
    db = Session()
    try:
        return db.query(WhatsAppProcessedMessage).filter_by(
            message_id=message_id
        ).first()
    finally:
        db.close()


def test_retry_schedule_delays(test_db):
    message_id = "schedule-test-001"

    db = test_db()
    db.add(
        WhatsAppProcessedMessage(
            message_id=message_id,
            status="processing",
        )
    )
    db.commit()
    db.close()

    # First failure: retry after approximately one minute.
    before = datetime.now(timezone.utc)

    whatsapp.update_whatsapp_message_status(
        message_id,
        "failed",
        error="First failure",
        increment_retry=True,
    )

    after = datetime.now(timezone.utc)

    record = get_record(test_db, message_id)

    assert record.retry_count == 1
    assert record.next_retry_at is not None

    scheduled = record.next_retry_at.replace(
        tzinfo=timezone.utc
    )

    assert before + timedelta(minutes=1) <= scheduled
    assert scheduled <= after + timedelta(minutes=1)

    # Second failure: retry after approximately five minutes.
    whatsapp.update_whatsapp_message_status(
        message_id,
        "failed",
        error="Second failure",
        increment_retry=True,
    )

    record = get_record(test_db, message_id)

    assert record.retry_count == 2
    assert record.next_retry_at is not None

    scheduled = record.next_retry_at.replace(
        tzinfo=timezone.utc
    )

    now = datetime.now(timezone.utc)

    assert now + timedelta(minutes=4, seconds=55) <= scheduled
    assert scheduled <= now + timedelta(minutes=5, seconds=5)

    # Third failure: no further automatic retry.
    whatsapp.update_whatsapp_message_status(
        message_id,
        "failed",
        error="Third failure",
        increment_retry=True,
    )

    record = get_record(test_db, message_id)

    assert record.retry_count == 3
    assert record.next_retry_at is None

    print("Retry scheduling delays: PASSED")


def test_retry_claim_respects_schedule(test_db):
    message_id = "schedule-test-002"

    db = test_db()
    db.add(
        WhatsAppProcessedMessage(
            message_id=message_id,
            status="failed",
            retry_count=1,
            next_retry_at=(
                datetime.now(timezone.utc)
                + timedelta(minutes=1)
            ),
        )
    )
    db.commit()
    db.close()

    # Claim must fail before the scheduled time.
    assert (
        whatsapp.claim_whatsapp_message_for_retry(message_id)
        is False
    )

    # Move the retry time into the past.
    db = test_db()
    record = db.query(WhatsAppProcessedMessage).filter_by(
        message_id=message_id
    ).first()

    record.next_retry_at = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    )

    db.commit()
    db.close()

    # Claim should now succeed.
    assert (
        whatsapp.claim_whatsapp_message_for_retry(message_id)
        is True
    )

    # A second worker must not claim the same message.
    assert (
        whatsapp.claim_whatsapp_message_for_retry(message_id)
        is False
    )

    print("Retry claim scheduling protection: PASSED")


def test_stale_message_recovery_schedules_retry(test_db):
    message_id = "schedule-test-003"

    db = test_db()
    db.add(
        WhatsAppProcessedMessage(
            message_id=message_id,
            status="processing",
            retry_count=0,
            processing_started_at=(
                datetime.now(timezone.utc)
                - timedelta(minutes=20)
            ),
        )
    )
    db.commit()
    db.close()

    recovered = whatsapp.recover_stale_whatsapp_messages(
        stale_after_minutes=15
    )

    assert recovered == 1

    record = get_record(test_db, message_id)

    assert record.status == "failed"
    assert record.retry_count == 1
    assert record.processing_started_at is None
    assert record.next_retry_at is not None

    print("Stale message recovery scheduling: PASSED")
