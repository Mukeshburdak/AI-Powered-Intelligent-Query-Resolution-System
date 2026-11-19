from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import text

# Load project environment variables.
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)

from backend.database.connection import engine


def migrate():
    with engine.begin() as connection:
        connection.execute(
            text("""
                CREATE UNIQUE INDEX IF NOT EXISTS
                uq_whatsapp_accounts_user_id
                ON whatsapp_accounts (user_id)
            """)
        )

    print("WhatsApp account user uniqueness migration: SUCCESS")


if __name__ == "__main__":
    migrate()