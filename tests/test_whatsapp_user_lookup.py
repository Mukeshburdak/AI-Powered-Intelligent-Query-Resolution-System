
from pathlib import Path
from dotenv import load_dotenv

# Load project .env before importing backend modules.
PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env", override=False)

from backend.database.connection import SessionLocal
from backend.database.models import WhatsAppAccount
from backend.api.routes_whatsapp import get_linked_user_id

db = SessionLocal()

try:
    accounts = (
        db.query(WhatsAppAccount)
        .filter(WhatsAppAccount.is_verified.is_(True))
        .order_by(WhatsAppAccount.user_id)
        .all()
    )

    print("\n========== WEBHOOK USER LOOKUP TEST ==========")

    assert accounts, "No verified WhatsApp accounts found."

    for account in accounts:
        actual_user_id = get_linked_user_id(account.phone_number)

        print(f"\nPhone: ****{account.phone_number[-4:]}")
        print(f"Expected user ID: {account.user_id}")
        print(f"Actual user ID:   {actual_user_id}")

        assert actual_user_id == account.user_id, (
            f"Incorrect user mapping for account {account.id}"
        )

    print("\nSUCCESS: All WhatsApp sender lookups passed.")

finally:
    db.close()
