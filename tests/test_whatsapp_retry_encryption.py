
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env", override=False)

from backend.api.routes_whatsapp import (
    encrypt_retry_payload,
    decrypt_retry_payload,
)


def test_encryption():
    original_payload = {
        "type": "text",
        "sender": "919876543210",
        "user_id": 3,
        "question": "What is the refund policy?",
    }

    encrypted = encrypt_retry_payload(original_payload)

    assert isinstance(encrypted, str)
    assert encrypted != str(original_payload)
    assert "919876543210" not in encrypted
    assert "refund policy" not in encrypted

    decrypted = decrypt_retry_payload(encrypted)

    assert decrypted == original_payload

    print("========== RETRY ENCRYPTION TEST ==========")
    print("Encryption: PASSED")
    print("Sensitive data hidden: PASSED")
    print("Decryption: PASSED")
    print("Payload integrity: PASSED")
    print("\nSUCCESS: Retry encryption test passed.")


if __name__ == "__main__":
    test_encryption()
