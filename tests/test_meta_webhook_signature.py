
import hashlib
import hmac
import json
import asyncio
from pathlib import Path

from dotenv import load_dotenv
from starlette.requests import Request
from starlette.background import BackgroundTasks

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env", override=False)

from backend.api import routes_whatsapp


async def run_tests():

    secret = routes_whatsapp.APP_SECRET

    assert secret, "WHATSAPP_APP_SECRET is missing."

    payload = {
        "object": "whatsapp_business_account",
        "entry": []
    }

    raw_body = json.dumps(payload).encode("utf-8")

    valid_signature = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    async def test_request(signature=None):

        headers = [
            (b"content-type", b"application/json")
        ]

        if signature is not None:
            headers.append(
                (
                    b"x-hub-signature-256",
                    signature.encode("utf-8"),
                )
            )

        async def receive():
            return {
                "type": "http.request",
                "body": raw_body,
                "more_body": False,
            }

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/whatsapp/webhook",
            "headers": headers,
            "query_string": b"",
            "server": ("testserver", 80),
            "client": ("127.0.0.1", 12345),
            "scheme": "http",
        }

        request = Request(scope, receive)

        return routes_whatsapp.verify_meta_signature(
            request,
            raw_body,
        )

    print("\n========== META SIGNATURE TEST ==========")

    # Test 1: Correct signature.
    assert await test_request(valid_signature) is True
    print("Valid signature: ACCEPTED")

    # Test 2: Incorrect signature.
    assert await test_request("sha256=invalid_signature") is False
    print("Invalid signature: REJECTED")

    # Test 3: Missing signature.
    assert await test_request() is False
    print("Missing signature: REJECTED")

    # Test 4: Modified request body.
    modified_body = raw_body + b" "

    async def modified_request():
        async def receive():
            return {
                "type": "http.request",
                "body": modified_body,
                "more_body": False,
            }

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/whatsapp/webhook",
            "headers": [
                (
                    b"x-hub-signature-256",
                    valid_signature.encode("utf-8"),
                )
            ],
            "query_string": b"",
            "server": ("testserver", 80),
            "client": ("127.0.0.1", 12345),
            "scheme": "http",
        }

        request = Request(scope, receive)

        return routes_whatsapp.verify_meta_signature(
            request,
            modified_body,
        )

    assert await modified_request() is False
    print("Modified body: REJECTED")

    print("\nSUCCESS: All Meta signature tests passed.")


if __name__ == "__main__":
    asyncio.run(run_tests())
