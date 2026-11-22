
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.config import STORAGE_DIR

DEFAULT_DB = STORAGE_DIR / "app.db"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{DEFAULT_DB.as_posix()}",
)

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    DEFAULT_DB.parent.mkdir(parents=True, exist_ok=True)

    from sqlalchemy import inspect

    from backend.database import models

    # Create any missing tables.
    Base.metadata.create_all(bind=engine)

    # Safely migrate existing databases.
    inspector = inspect(engine)

    if "whatsapp_processed_messages" not in inspector.get_table_names():
        return

    columns = {
        column["name"]
        for column in inspector.get_columns(
            "whatsapp_processed_messages"
        )
    }

    if "next_retry_at" not in columns:
        with engine.begin() as connection:

            if engine.dialect.name == "sqlite":
                connection.exec_driver_sql(
                    """
                    ALTER TABLE whatsapp_processed_messages
                    ADD COLUMN next_retry_at DATETIME
                    """
                )

            elif engine.dialect.name == "postgresql":
                connection.exec_driver_sql(
                    """
                    ALTER TABLE whatsapp_processed_messages
                    ADD COLUMN next_retry_at TIMESTAMP WITH TIME ZONE
                    """
                )

            else:
                raise RuntimeError(
                    "Unsupported database dialect for WhatsApp retry migration."
                )

    # Ensure the retry scheduling index exists.
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE INDEX IF NOT EXISTS
            ix_whatsapp_processed_messages_next_retry_at
            ON whatsapp_processed_messages (next_retry_at)
            """
        )