
from backend.database.connection import SessionLocal
from backend.database.models import WhatsAppAccount

db = SessionLocal()

try:
    accounts = (
        db.query(WhatsAppAccount)
        .order_by(WhatsAppAccount.user_id)
        .all()
    )

    print("\n========== WHATSAPP ACCOUNT MAPPING ==========")

    if not accounts:
        print("No linked WhatsApp accounts found.")

    for account in accounts:
        phone = str(account.phone_number)

        print(f"\nAccount ID: {account.id}")
        print(f"Phone ending: ****{phone[-4:]}")
        print(f"Linked User ID: {account.user_id}")
        print(f"Verified: {account.is_verified}")

    print("\n==============================================")

finally:
    db.close()
