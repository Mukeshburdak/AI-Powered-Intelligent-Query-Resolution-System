
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from starlette.requests import Request
from starlette.background import BackgroundTasks

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env", override=False)

from backend.api import routes_whatsapp


async def main():

    sender = "19999999999"

    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": sender,
                        "id": "unlinked-test-001",
                        "type": "text",
                        "text": {
                            "body": "Show me my uploaded documents"
                        }
                    }]
                }
            }]
        }]
    }

    body = json.dumps(payload).encode("utf-8")

    async def receive():
        return {
            "type": "http.request",
            "body": body,
            "more_body": False
        }

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/whatsapp/webhook",
        "headers": [
            (b"content-type", b"application/json")
        ],
        "query_string": b"",
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 12345),
        "scheme": "http"
    }

    request = Request(scope, receive)
    background_tasks = BackgroundTasks()

    response = await routes_whatsapp.receive_webhook(
        request,
        background_tasks
    )

    assert response == {"status": "received"}

    # An unlinked sender must not trigger document or query processing.
    forbidden_tasks = {
        routes_whatsapp.process_incoming_message,
        routes_whatsapp.process_incoming_document,
    }

    assert not any(
        task.func in forbidden_tasks
        for task in background_tasks.tasks
    ), "SECURITY FAILURE: Unlinked sender triggered processing!"

    # The sender should receive linking instructions.
    assert any(
        task.func == routes_whatsapp.send_whatsapp_message
        and task.args[0] == sender
        and "not linked" in task.args[1].lower()
        for task in background_tasks.tasks
    ), "Expected account-linking instructions were not queued."

    print("\n========== UNLINKED USER SECURITY TEST ==========")
    print("Sender: ****" + sender[-4:])
    print("Question processing: BLOCKED")
    print("Document processing: BLOCKED")
    print("Linking instructions: QUEUED")
    print("\nSUCCESS: Unlinked sender was rejected.")


if __name__ == "__main__":
    asyncio.run(main())
