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

        if "retry_count" not in columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE whatsapp_processed_messages
                    ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0
                    """
                )
            )
            print("Added retry_count column.")

        if "last_error" not in columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE whatsapp_processed_messages
                    ADD COLUMN last_error TEXT
                    """
                )
            )
            print("Added last_error column.")

    print("\nSUCCESS: WhatsApp message table migration completed.")


if __name__ == "__main__":
    migrate()