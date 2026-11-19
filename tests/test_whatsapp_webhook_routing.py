import pytest
import json
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
from backend.database.models import WhatsAppAccount
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
async def test_webhook_routing():

    db = SessionLocal()

    try:
        accounts = (
            db.query(WhatsAppAccount)
            .filter(WhatsAppAccount.is_verified.is_(True))
            .order_by(WhatsAppAccount.user_id)
            .all()
        )

        assert accounts, "No verified WhatsApp accounts found."

        print("\n========== WEBHOOK ROUTING TEST ==========")

        for account in accounts:

            sender = account.phone_number
            expected_user_id = account.user_id

            question = f"Test question for user {expected_user_id}"

            # Use a unique ID for every test execution.
            message_id = (
                f"test-message-{expected_user_id}-"
                f"{uuid.uuid4().hex}"
            )

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

            request = await create_request(payload)
            background_tasks = BackgroundTasks()

            response = await routes_whatsapp.receive_webhook(
                request,
                background_tasks,
            )

            assert response == {"status": "received"}

            matching_tasks = [
                task for task in background_tasks.tasks
                if task.func in (
                    routes_whatsapp.process_incoming_message,
                    routes_whatsapp.process_tracked_incoming_message,
                )
            ]

            assert len(matching_tasks) == 1, (
                f"Expected exactly one text-processing task for "
                f"user {expected_user_id}; "
                f"found {len(matching_tasks)}."
            )

            task = matching_tasks[0]

            print(f"\nPhone ending: ****{sender[-4:]}")
            print(f"Expected user ID: {expected_user_id}")
            print(f"Task function: {task.func.__name__}")

            # The tracked function receives message ID, sender,
            # question, and user ID.
            if task.func == routes_whatsapp.process_tracked_incoming_message:

                (
                    actual_message_id,
                    actual_sender,
                    actual_question,
                    actual_user_id,
                ) = task.args

                assert actual_message_id == message_id

            else:

                (
                    actual_sender,
                    actual_question,
                    actual_user_id,
                ) = task.args

            print(f"Actual user ID: {actual_user_id}")
            print(f"Question: {actual_question}")

            assert actual_sender == sender
            assert actual_question == question
            assert actual_user_id == expected_user_id

            print("Webhook routing: PASSED")

        print("\nSUCCESS: Webhook routing passed for all accounts.")

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_webhook_routing())
