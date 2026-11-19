from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import inspect, text

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

from backend.database.connection import engine


table_name = "whatsapp_processed_messages"
column_name = "processing_started_at"

with engine.begin() as connection:
    inspector = inspect(connection)

    columns = {
        column["name"]
        for column in inspector.get_columns(table_name)
    }

    if column_name not in columns:
        connection.execute(
            text(
                f"ALTER TABLE {table_name} "
                f"ADD COLUMN {column_name} DATETIME"
            )
        )
        print("SUCCESS: processing_started_at column added.")
    else:
        print("INFO: processing_started_at column already exists.")

    updated_columns = {
        column["name"]
        for column in inspect(connection).get_columns(table_name)
    }

    print("Current columns:", sorted(updated_columns))