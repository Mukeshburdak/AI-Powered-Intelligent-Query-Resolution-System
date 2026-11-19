
import json
import pytest
import asyncio
import hashlib
import hmac
import uuid
from pathlib import Path
from dotenv import load_dotenv

from starlette.requests import Request
from starlette.background import BackgroundTasks

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env", override=False)

from backend.database.connection import SessionLocal
from backend.database.models import (
    WhatsAppAccount,
    WhatsAppProcessedMessage,
)
from backend.api import routes_whatsapp


def create_signature(body: bytes) -> str:
    """Generate a valid Meta webhook signature."""

    app_secret = routes_whatsapp.APP_SECRET

    assert app_secret, (
        "WHATSAPP_APP_SECRET is missing from the environment."
    )

    digest = hmac.new(
        app_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    return f"sha256={digest}"


async def create_request(payload: dict) -> Request:
    """Create a signed webhook request."""

    body = json.dumps(payload).encode("utf-8")
    signature = create_signature(body)

    async def receive():
        return {
            "type": "http.request",
            "body": body,
            "more_body": False,
        }

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/whatsapp/webhook",
        "headers": [
            (b"content-type", b"application/json"),
            (
                b"x-hub-signature-256",
                signature.encode("utf-8"),
            ),
        ],
        "query_string": b"",
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 12345),
        "scheme": "http",
    }

    return Request(scope, receive)

@pytest.mark.asyncio
async def test_duplicate_messages():

    assert routes_whatsapp.APP_SECRET, (
        "WHATSAPP_APP_SECRET is missing."
    )

    db = SessionLocal()

    message_id = f"dedupe-test-{uuid.uuid4().hex}"

    try:
        account = (
            db.query(WhatsAppAccount)
            .filter(WhatsAppAccount.is_verified.is_(True))
            .order_by(WhatsAppAccount.user_id)
            .first()
        )

        assert account, "No verified WhatsApp account found."

        sender = account.phone_number
        question = "Duplicate message security test"

        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": sender,
                            "id": message_id,
                            "type": "text",
                            "text": {
                                "body": question
                            }
                        }]
                    }
                }]
            }]
        }

        print("\n========== DUPLICATE MESSAGE TEST ==========")

        # First delivery.
        request1 = await create_request(payload)
        tasks1 = BackgroundTasks()

        response1 = await routes_whatsapp.receive_webhook(
            request1,
            tasks1,
        )

        assert response1 == {"status": "received"}

        first_processing_tasks = [
            task for task in tasks1.tasks
            if task.func in (
                routes_whatsapp.process_incoming_message,
                routes_whatsapp.process_tracked_incoming_message,
            )
        ]

        assert len(first_processing_tasks) == 1, (
            "First delivery should queue exactly one text-processing task. "
            f"Found {len(first_processing_tasks)}."
        )

        first_task = first_processing_tasks[0]

        print("First delivery: ACCEPTED")
        print("Processing function:", first_task.func.__name__)
        print("First processing tasks:", len(first_processing_tasks))

        # Second delivery with exactly the same message ID.
        request2 = await create_request(payload)
        tasks2 = BackgroundTasks()

        response2 = await routes_whatsapp.receive_webhook(
            request2,
            tasks2,
        )

        assert response2 == {"status": "received"}

        second_processing_tasks = [
            task for task in tasks2.tasks
            if task.func in (
                routes_whatsapp.process_incoming_message,
                routes_whatsapp.process_tracked_incoming_message,
            )
        ]

        assert len(second_processing_tasks) == 0, (
            "Duplicate delivery must not queue another processing task."
        )

        print("Second delivery: DUPLICATE REJECTED")
        print("Second processing tasks:", len(second_processing_tasks))

        # Verify only one database record exists.
        db.expire_all()

        records = (
            db.query(WhatsAppProcessedMessage)
            .filter(
                WhatsAppProcessedMessage.message_id == message_id
            )
            .all()
        )

        assert len(records) == 1, (
            f"Expected exactly one database record, found {len(records)}."
        )

        print("Database records:", len(records))

        print(
            "\nSUCCESS: Duplicate message protection passed."
        )

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_duplicate_messages())
