
from sqlalchemy import inspect, text
from backend.database.connection import engine


def migrate():
    inspector = inspect(engine)

    columns = {
        column["name"]
        for column in inspector.get_columns(
            "whatsapp_processed_messages"
        )
    }

    with engine.begin() as connection:
        if "retry_payload" not in columns:
            connection.execute(
                text("""
                    ALTER TABLE whatsapp_processed_messages
                    ADD COLUMN retry_payload TEXT
                """)
            )
            print("Added retry_payload column.")
        else:
            print("retry_payload column already exists.")

    print("\nSUCCESS: Retry payload migration completed.")


if __name__ == "__main__":
    migrate()
