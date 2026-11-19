from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)

from backend.database.connection import SessionLocal
from backend.database.models import User, WhatsAppAccount


def test_whatsapp_account_uniqueness():
    db = SessionLocal()
    user_id = None

    try:
        user = User(
            name="Uniqueness Test User",
            email="uniqueness_test@example.com",
            password_hash="test_password_hash",
            is_active=True,
        )

        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

        first_account = WhatsAppAccount(
            user_id=user_id,
            phone_number="919999000011",
            is_verified=True,
        )

        db.add(first_account)
        db.commit()

        print("First WhatsApp account: PASSED")

        second_account = WhatsAppAccount(
            user_id=user_id,
            phone_number="919999000012",
            is_verified=True,
        )

        db.add(second_account)

        try:
            db.commit()
            raise AssertionError(
                "Database accepted a second WhatsApp number!"
            )

        except IntegrityError:
            db.rollback()
            print("Second WhatsApp account rejected: PASSED")

    finally:
        if user_id is not None:
            db.query(WhatsAppAccount).filter_by(
                user_id=user_id
            ).delete()

            db.query(User).filter_by(id=user_id).delete()
            db.commit()

        db.close()


if __name__ == "__main__":
    test_whatsapp_account_uniqueness()