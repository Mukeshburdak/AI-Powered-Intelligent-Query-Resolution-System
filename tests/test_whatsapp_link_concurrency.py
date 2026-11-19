
from pathlib import Path
from dotenv import load_dotenv
import hashlib
import threading
import uuid

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

# Load environment variables before backend imports.
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)

from backend.api import routes_whatsapp
from backend.database.connection import SessionLocal
from backend.database.models import (
    User,
    WhatsAppLinkToken,
    WhatsAppAccount,
)


def generate_phone():
    return str(9100000000 + uuid.uuid4().int % 899999999)


def create_token(db, user_id, code):
    token_hash = hashlib.sha256(
        code.encode("utf-8")
    ).hexdigest()

    token = WhatsAppLinkToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc)
        + timedelta(minutes=10),
        used_at=None,
    )

    db.add(token)
    db.commit()


def test_same_linking_code_cannot_be_used_twice():
    db = SessionLocal()

    user_id = None
    code = f"TESTLINK{uuid.uuid4().hex[:16]}"

    phone1 = generate_phone()
    phone2 = generate_phone()

    try:
        # Create a unique test user.
        user = User(
            name="Concurrency Test User",
            email=f"link_concurrency_{uuid.uuid4().hex[:12]}@example.com",
            password_hash="test_password_hash",
            is_active=True,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        user_id = user.id

        # Create one unique linking token.
        create_token(db, user_id, code)

    finally:
        db.close()

    barrier = threading.Barrier(2)

    def attempt_link(sender):
        barrier.wait()

        return routes_whatsapp.link_whatsapp_account(
            sender=sender,
            code=code,
        )

    try:
        # Attempt to use the same token simultaneously.
        with ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(attempt_link, phone1)
            future2 = executor.submit(attempt_link, phone2)

            result1 = future1.result()
            result2 = future2.result()

        results = [result1, result2]

        successful = [
            result for result in results
            if "linked successfully" in result.lower()
        ]

        rejected = [
            result for result in results
            if "linked successfully" not in result.lower()
        ]

        assert len(successful) == 1, results
        assert len(rejected) == 1, results

        print("Concurrent token usage: PASSED")
        print("Exactly one linking attempt succeeded: PASSED")
        print("Second linking attempt rejected: PASSED")

        # Verify database state.
        check_db = SessionLocal()

        try:
            token = check_db.query(
                WhatsAppLinkToken
            ).filter(
                WhatsAppLinkToken.user_id == user_id
            ).first()

            accounts = check_db.query(
                WhatsAppAccount
            ).filter(
                WhatsAppAccount.user_id == user_id
            ).all()

            assert token is not None
            assert token.used_at is not None
            assert len(accounts) == 1

            print("Token consumed exactly once: PASSED")
            print("Only one WhatsApp account linked: PASSED")

        finally:
            check_db.close()

    finally:
        # Clean up test records.
        cleanup_db = SessionLocal()

        try:
            if user_id is not None:
                cleanup_db.query(
                    WhatsAppAccount
                ).filter(
                    WhatsAppAccount.user_id == user_id
                ).delete(synchronize_session=False)

                cleanup_db.query(
                    WhatsAppLinkToken
                ).filter(
                    WhatsAppLinkToken.user_id == user_id
                ).delete(synchronize_session=False)

                cleanup_db.query(
                    User
                ).filter(
                    User.id == user_id
                ).delete(synchronize_session=False)

                cleanup_db.commit()

        finally:
            cleanup_db.close()


def test_whatsapp_account_linking_rules():
    db = SessionLocal()

    suffix = uuid.uuid4().hex[:12]

    email1 = f"link_test1_{suffix}@example.com"
    email2 = f"link_test2_{suffix}@example.com"

    code1 = f"FIRST{suffix}"
    code2 = f"SECOND{suffix}"
    code3 = f"THIRD{suffix}"

    phone1 = generate_phone()
    phone2 = generate_phone()

    user1_id = None
    user2_id = None

    try:
        user1 = User(
            name="Link Test User One",
            email=email1,
            password_hash="test_password_hash",
            is_active=True,
        )

        user2 = User(
            name="Link Test User Two",
            email=email2,
            password_hash="test_password_hash",
            is_active=True,
        )

        db.add_all([user1, user2])
        db.commit()

        db.refresh(user1)
        db.refresh(user2)

        user1_id = user1.id
        user2_id = user2.id

        # Create three different linking tokens.
        create_token(db, user1_id, code1)
        create_token(db, user1_id, code2)
        create_token(db, user2_id, code3)

    finally:
        db.close()

    try:
        # Case 1: First WhatsApp number links successfully.
        result1 = routes_whatsapp.link_whatsapp_account(
            sender=phone1,
            code=code1,
        )

        assert "linked successfully" in result1.lower(), result1
        print("New WhatsApp number linking: PASSED")

        # Case 2: Same application user tries another number.
        result2 = routes_whatsapp.link_whatsapp_account(
            sender=phone2,
            code=code2,
        )

        assert "already linked" in result2.lower(), result2
        print("Second number for same user rejected: PASSED")

        # Case 3: Another application user tries the first number.
        result3 = routes_whatsapp.link_whatsapp_account(
            sender=phone1,
            code=code3,
        )

        assert "already linked" in result3.lower(), result3
        print("Number already linked to another user rejected: PASSED")

    finally:
        cleanup_db = SessionLocal()

        try:
            cleanup_db.query(
                WhatsAppAccount
            ).filter(
                WhatsAppAccount.user_id.in_(
                    [user1_id, user2_id]
                )
            ).delete(synchronize_session=False)

            cleanup_db.query(
                WhatsAppLinkToken
            ).filter(
                WhatsAppLinkToken.user_id.in_(
                    [user1_id, user2_id]
                )
            ).delete(synchronize_session=False)

            cleanup_db.query(
                User
            ).filter(
                User.id.in_(
                    [user1_id, user2_id]
                )
            ).delete(synchronize_session=False)

            cleanup_db.commit()

        finally:
            cleanup_db.close()


if __name__ == "__main__":
    test_same_linking_code_cannot_be_used_twice()
    test_whatsapp_account_linking_rules()

    print("\nALL WHATSAPP LINKING TESTS PASSED.")
