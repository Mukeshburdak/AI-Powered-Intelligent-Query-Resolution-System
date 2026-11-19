import os
import json
import uuid
import re
import hmac
import hashlib
import secrets
import logging
import urllib.request
import urllib.error

from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from fastapi import (
    APIRouter,
    Request,
    BackgroundTasks,
    Depends,
    HTTPException,
)
from fastapi.responses import PlainTextResponse
from sqlalchemy import delete, select, update, or_, case
from sqlalchemy.orm import Session
from backend.database.models import (
    WhatsAppAccount,
    WhatsAppLinkToken,
    WhatsAppProcessedMessage,
    User,
)
from sqlalchemy.exc import IntegrityError
from backend.database.connection import SessionLocal, get_db
from backend.database.models import (
    WhatsAppAccount,
    WhatsAppLinkToken,
    User,
)
from backend.security.auth import get_current_user
from backend.orchestration.orchestrator import answer_query

from backend.config import (
    ALLOWED_DOCUMENT_EXTENSIONS,
    MAX_UPLOAD_SIZE_MB,
    SAMPLE_DOCUMENTS_DIR,
)
from backend.ingestion.ingestion_pipeline import ingest_file
from backend.retrieval.vector_store import vector_store
from cryptography.fernet import Fernet, InvalidToken

router = APIRouter(prefix="/api/whatsapp", tags=["WhatsApp"])

logger = logging.getLogger(__name__)

def link_whatsapp_account(sender: str, code: str) -> str:
    db = SessionLocal()

    try:
        token_hash = hashlib.sha256(
            code.encode("utf-8")
        ).hexdigest()

        token = db.scalar(
            select(WhatsAppLinkToken).where(
                WhatsAppLinkToken.token_hash == token_hash,
                WhatsAppLinkToken.used_at.is_(None),
            )
        )

        if not token:
            return (
                "Invalid or already-used linking code. "
                "Please generate a new code from your account."
            )

        now = datetime.now(timezone.utc)
        expiry = token.expires_at

        # SQLite may return timezone-naive datetimes.
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

        if expiry <= now:
            return (
                "Your linking code has expired. "
                "Please generate a new one."
            )

        user = db.get(User, token.user_id)

        if not user or not user.is_active:
            return "Your application account is unavailable."

        existing = db.scalar(
            select(WhatsAppAccount).where(
                WhatsAppAccount.phone_number == sender
            )
        )

        if existing and existing.user_id != user.id:
            return (
                "This WhatsApp number is already linked "
                "to another application account."
            )

        # Atomically claim the linking token.
        # Only one concurrent request can successfully update it.
        claim_result = db.execute(
            update(WhatsAppLinkToken)
            .where(
                WhatsAppLinkToken.id == token.id,
                WhatsAppLinkToken.used_at.is_(None),
                WhatsAppLinkToken.expires_at > now.replace(tzinfo=None),
            )
            .values(used_at=now)
            .execution_options(synchronize_session=False)
        )

        if claim_result.rowcount != 1:
            db.rollback()
            return (
                "Invalid, expired, or already-used linking code. "
                "Please generate a new code."
            )

        if existing:
            existing.is_verified = True
        else:
            account = WhatsAppAccount(
                user_id=user.id,
                phone_number=sender,
                is_verified=True,
            )
            db.add(account)

        # Token consumption and account linking commit together.
        db.commit()

        return (
            "WhatsApp account linked successfully!\n\n"
            f"Application account: {user.email}\n\n"
            "You can now upload documents and ask questions "
            "about your own documents here."
        )

    except IntegrityError:
        db.rollback()
        logger.warning(
            "WhatsApp account linking rejected by a database uniqueness constraint."
        )
        return (
            "This application account or WhatsApp number is already linked. "
            "Each application account can link only one WhatsApp number."
        )

    except Exception:
        db.rollback()
        logger.exception("WhatsApp account linking failed.")
        return "Account linking failed. Please try again."

    finally:
        db.close()

def get_linked_user_id(sender: str):
    db = SessionLocal()
    try:
        account = db.execute(
            select(WhatsAppAccount.user_id)
            .join(User, User.id == WhatsAppAccount.user_id)
            .where(
                WhatsAppAccount.phone_number == sender,
                WhatsAppAccount.is_verified.is_(True),
                User.is_active.is_(True),
            )
        ).first()

        return account[0] if account else None
    finally:
        db.close()


def retry_whatsapp_message(message_id: str) -> bool:
    """
    Retry a failed WhatsApp message using its encrypted payload.

    Only one worker can claim a message for retry.
    """

    if not claim_whatsapp_message_for_retry(message_id):
        return False

    # Phase 1: Retrieve and validate the retry payload.
    try:
        payload = get_whatsapp_retry_payload(message_id)

        if not payload:
            raise ValueError("Retry payload is missing.")

        message_type = payload.get("type")
        sender = payload.get("sender")
        user_id = payload.get("user_id")

        if not sender or not user_id:
            raise ValueError("Retry payload is incomplete.")

        linked_user_id = get_linked_user_id(sender)

        if linked_user_id is None or linked_user_id != user_id:
            raise PermissionError(
                "WhatsApp sender is no longer linked to the original user."
            )

        # Phase 2: Process the original message.
        if message_type == "text":
            question = payload.get("question")

            if not question:
                raise ValueError("Retry question is missing.")

            success = process_incoming_message(
                sender,
                question,
                user_id,
            )

        elif message_type == "document":
            media_id = payload.get("media_id")
            filename = payload.get("filename")

            if not media_id or not filename:
                raise ValueError("Retry document details are missing.")

            success = process_incoming_document(
                sender,
                media_id,
                filename,
                user_id,
                message_id=message_id,
            )

        else:
            raise ValueError(
                f"Unsupported retry message type: {message_type}"
            )

        error = (
            None
            if success
            else "Retry processing or WhatsApp reply delivery failed."
        )

    except Exception as exc:
        logger.exception(
            "WhatsApp retry processing failed for message: %s",
            message_id,
        )

        success = False
        error = str(exc)

    # Phase 3: Record the result exactly once.
    try:
        if success:
            update_whatsapp_message_status(
                message_id,
                "processed",
            )

            return True

        update_whatsapp_message_status(
            message_id,
            "failed",
            error=error,
            increment_retry=True,
        )

        return False

    except Exception:
        logger.exception(
            "Could not record WhatsApp retry result for message: %s",
            message_id,
        )

        return False



def get_due_whatsapp_retry_message_ids(
    limit: int = 20,
) -> list[str]:
    """
    Return failed WhatsApp messages whose scheduled retry time
    has arrived.

    Messages are only selected here. Actual claiming is handled
    atomically by retry_whatsapp_message().
    """

    if limit <= 0:
        raise ValueError("limit must be greater than zero.")

    db = SessionLocal()

    try:
        now = datetime.now(timezone.utc)

        message_ids = db.execute(
            select(WhatsAppProcessedMessage.message_id)
            .where(
                WhatsAppProcessedMessage.status == "failed",
                WhatsAppProcessedMessage.retry_count < 3,
                or_(
                    WhatsAppProcessedMessage.next_retry_at.is_(None),
                    WhatsAppProcessedMessage.next_retry_at <= now,
                ),
            )
            .order_by(
                WhatsAppProcessedMessage.next_retry_at.asc()
            )
            .limit(limit)
        ).scalars().all()

        return list(message_ids)

    except Exception:
        logger.exception(
            "Could not retrieve due WhatsApp retry messages."
        )
        raise

    finally:
        db.close()


def register_whatsapp_message(
    message_id: str,
    retry_payload: dict | None = None,
) -> bool:
    """
    Atomically register a WhatsApp message ID
    and optionally store its encrypted retry payload.

    Returns True for a new message and False for a duplicate.
    """

    db = SessionLocal()

    try:
        encrypted_payload = (
            encrypt_retry_payload(retry_payload)
            if retry_payload is not None
            else None
        )

        record = WhatsAppProcessedMessage(
            message_id=message_id,
            status="received",
            retry_payload=encrypted_payload,
        )

        db.add(record)
        db.commit()

        logger.info(
            "WhatsApp message registered: %s",
            message_id,
        )

        return True

    except IntegrityError:
        db.rollback()

        logger.info(
            "Duplicate WhatsApp message ignored: %s",
            message_id,
        )

        return False

    except Exception:
        db.rollback()
        logger.exception(
            "Could not register WhatsApp message."
        )
        raise

    finally:
        db.close()

def claim_whatsapp_message_for_retry(
    message_id: str,
    max_attempts: int = 3,
) -> bool:
    """
    Atomically claim a failed WhatsApp message for retry.

    A message can only be claimed when its scheduled retry time
    has arrived. Only one worker can claim it.
    """

    db = SessionLocal()

    try:
        now = datetime.now(timezone.utc)

        result = db.execute(
            update(WhatsAppProcessedMessage)
            .where(
                WhatsAppProcessedMessage.message_id == message_id,
                WhatsAppProcessedMessage.status == "failed",
                WhatsAppProcessedMessage.retry_count < max_attempts,
                or_(
                    WhatsAppProcessedMessage.next_retry_at.is_(None),
                    WhatsAppProcessedMessage.next_retry_at <= now,
                ),
            )
            .values(
                status="processing",
                processing_started_at=now,
                next_retry_at=None,
            )
        )

        db.commit()

        claimed = result.rowcount == 1

        if claimed:
            logger.info(
                "WhatsApp message claimed for retry: %s",
                message_id,
            )
        else:
            logger.info(
                "WhatsApp message is not eligible for retry: %s",
                message_id,
            )

        return claimed

    except Exception:
        db.rollback()
        logger.exception(
            "Could not claim WhatsApp message for retry."
        )
        raise

    finally:
        db.close()


def recover_stale_whatsapp_messages(
    stale_after_minutes: int = 15,
) -> int:
    """
    Recover messages stuck in processing.

    Recovered messages are marked failed and scheduled for retry
    according to their updated retry count.
    """

    if stale_after_minutes <= 0:
        raise ValueError("stale_after_minutes must be greater than zero.")

    db = SessionLocal()

    try:
        now = datetime.now(timezone.utc)

        cutoff_time = now - timedelta(
            minutes=stale_after_minutes
        )

        # Recover messages that exceeded the processing timeout.
        result = db.execute(
            update(WhatsAppProcessedMessage)
            .where(
                WhatsAppProcessedMessage.status == "processing",
                WhatsAppProcessedMessage.processing_started_at.is_not(None),
                WhatsAppProcessedMessage.processing_started_at < cutoff_time,
            )
            .values(
                status="failed",
                last_error="Processing interrupted or timed out.",
                processing_started_at=None,
                retry_count=WhatsAppProcessedMessage.retry_count + 1,
            )
            .returning(
                WhatsAppProcessedMessage.message_id,
                WhatsAppProcessedMessage.retry_count,
            )
        )

        recovered_messages = result.all()

        # Schedule eligible retries based on the updated attempt count.
        for message_id, retry_count in recovered_messages:

            if retry_count == 1:
                delay_minutes = 1
            elif retry_count == 2:
                delay_minutes = 5
            else:
                delay_minutes = None

            next_retry_at = (
                now + timedelta(minutes=delay_minutes)
                if delay_minutes is not None
                else None
            )

            db.execute(
                update(WhatsAppProcessedMessage)
                .where(
                    WhatsAppProcessedMessage.message_id == message_id
                )
                .values(next_retry_at=next_retry_at)
            )

        db.commit()

        recovered_count = len(recovered_messages)

        logger.info(
            "Recovered %s stale WhatsApp messages.",
            recovered_count,
        )

        return recovered_count

    except Exception:
        db.rollback()
        logger.exception(
            "Failed to recover stale WhatsApp messages."
        )
        raise

    finally:
        db.close()


def get_whatsapp_retry_payload(message_id: str) -> dict | None:
    """Retrieve and decrypt a stored retry payload."""

    db = SessionLocal()

    try:
        record = db.execute(
            select(WhatsAppProcessedMessage).where(
                WhatsAppProcessedMessage.message_id == message_id
            )
        ).scalar_one_or_none()

        if record is None:
            return None

        if not record.retry_payload:
            return None

        return decrypt_retry_payload(record.retry_payload)

    except Exception:
        logger.exception(
            "Could not retrieve WhatsApp retry payload: %s",
            message_id,
        )
        raise

    finally:
        db.close()

def get_whatsapp_retry_owner(message_id: str) -> int | None:
    """Return the application user ID associated with a retry message."""

    db = SessionLocal()

    try:
        record = db.execute(
            select(WhatsAppProcessedMessage).where(
                WhatsAppProcessedMessage.message_id == message_id
            )
        ).scalar_one_or_none()

        if record is None or not record.retry_payload:
            return None

        payload = decrypt_retry_payload(record.retry_payload)
        user_id = payload.get("user_id")

        if not isinstance(user_id, int) or isinstance(user_id, bool):
            return None

        return user_id

    except Exception:
        logger.exception(
            "Could not verify WhatsApp retry ownership: %s",
            message_id,
        )
        raise

    finally:
        db.close()


def update_whatsapp_message_status(
    message_id: str,
    status: str,
    error: str | None = None,
    increment_retry: bool = False,
) -> None:
    """Atomically update WhatsApp status and retry scheduling."""

    allowed_statuses = {
        "received",
        "processing",
        "processed",
        "failed",
    }

    if status not in allowed_statuses:
        raise ValueError("Invalid WhatsApp message status.")

    if increment_retry and status != "failed":
        raise ValueError(
            "Retry count can only be incremented for failed messages."
        )

    db = SessionLocal()

    try:
        now = datetime.now(timezone.utc)

        values = {
            "status": status,
            "last_error": error[:1000] if error else None,
        }

        if status == "processing":
            values["processing_started_at"] = now
            values["next_retry_at"] = None

        else:
            values["processing_started_at"] = None

        if status == "processed":
            values["next_retry_at"] = None

        if increment_retry:
            current_retry_count = (
                WhatsAppProcessedMessage.retry_count
            )

            # Calculate the retry time using the existing database
            # counter value. Both changes happen in one UPDATE.
            values["retry_count"] = current_retry_count + 1

            values["next_retry_at"] = case(
                (
                    current_retry_count == 0,
                    now + timedelta(minutes=1),
                ),
                (
                    current_retry_count == 1,
                    now + timedelta(minutes=5),
                ),
                else_=None,
            )

        result = db.execute(
            update(WhatsAppProcessedMessage)
            .where(
                WhatsAppProcessedMessage.message_id == message_id
            )
            .values(**values)
        )

        if result.rowcount == 0:
            raise ValueError(
                f"WhatsApp message not found: {message_id}"
            )

        db.commit()

        logger.info(
            "WhatsApp message status updated: %s -> %s",
            message_id,
            status,
        )

    except Exception:
        db.rollback()

        logger.exception(
            "Could not update WhatsApp message status."
        )
        raise

    finally:
        db.close()


def process_link_message(sender: str, code: str):
    """Validate a one-time code and send the linking result to WhatsApp."""

    reply = link_whatsapp_account(sender, code)

    try:
        send_whatsapp_message(sender, reply)
    except Exception:
        logger.exception("Could not send WhatsApp account-linking response.")


@router.post("/link-code")
def generate_whatsapp_link_code(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a temporary code for linking a WhatsApp account."""

    code = f"{secrets.randbelow(100_000_000):08d}"
    token_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=10)

    try:
        # Invalidate previous unused codes for this user.
        db.execute(
            delete(WhatsAppLinkToken).where(
                WhatsAppLinkToken.user_id == current_user.id,
                WhatsAppLinkToken.used_at.is_(None),
            )
        )

        token = WhatsAppLinkToken(
            user_id=current_user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        db.add(token)
        db.commit()

        return {
            "success": True,
            "link_code": code,
            "expires_in_minutes": 10,
            "instruction": (
                f"Send LINK {code} to your WhatsApp Business number."
            ),
        }

    except Exception:
        db.rollback()
        logger.exception("Could not generate WhatsApp linking code.")
        raise HTTPException(
            status_code=500,
            detail="Could not generate a WhatsApp linking code.",
        )
@router.post("/retry/{message_id}", status_code=202)
def retry_whatsapp_message_endpoint(
    message_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    """Allow an authenticated user to retry their own failed WhatsApp message."""

    owner_id = get_whatsapp_retry_owner(message_id)

    if owner_id is None:
        raise HTTPException(
            status_code=404,
            detail="Retry message not found.",
        )

    if owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You cannot retry this message.",
        )

    background_tasks.add_task(
        retry_whatsapp_message,
        message_id,
    )

    return {
        "success": True,
        "status": "queued",
        "message": "WhatsApp message retry has been queued.",
    }

# --------------------------------------------------
# ENVIRONMENT CONFIGURATION
# --------------------------------------------------

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
APP_SECRET = os.getenv("WHATSAPP_APP_SECRET")

API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v27.0")

MAX_UPLOAD_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

ALLOWED_MEDIA_HOSTS = {
    "lookaside.fbsbx.com",
    "graph.facebook.com",
}
RETRY_ENCRYPTION_KEY = os.getenv(
    "WHATSAPP_RETRY_ENCRYPTION_KEY"
)

retry_cipher = (
    Fernet(RETRY_ENCRYPTION_KEY.encode("utf-8"))
    if RETRY_ENCRYPTION_KEY
    else None
)

def verify_meta_signature(
    request: Request,
    raw_body: bytes,
) -> bool:
    """
    Verify Meta's WhatsApp webhook signature using HMAC-SHA256.
    """

    if not APP_SECRET:
        logger.error(
            "WhatsApp App Secret is not configured."
        )
        return False

    signature = request.headers.get(
        "X-Hub-Signature-256",
        "",
    )

    if not signature.startswith("sha256="):
        logger.warning(
            "Meta signature header is missing or malformed."
        )
        return False

    received_hash = signature.removeprefix("sha256=")

    expected_hash = hmac.new(
        APP_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    # Compare only hashes. Never log the App Secret.
    signature_valid = hmac.compare_digest(
        received_hash,
        expected_hash,
    )

    if not signature_valid:
        logger.warning(
            "Meta signature mismatch. "
            "Received hash length: %s, expected hash length: %s",
            len(received_hash),
            len(expected_hash),
        )
        return False

    logger.info(
        "Meta webhook signature verified successfully."
    )

    return True

def encrypt_retry_payload(payload: dict) -> str:
    """Encrypt a retry payload before database storage."""

    if retry_cipher is None:
        raise RuntimeError(
            "WhatsApp retry encryption key is not configured."
        )

    serialized = json.dumps(payload).encode("utf-8")

    return retry_cipher.encrypt(serialized).decode("utf-8")


def decrypt_retry_payload(encrypted_payload: str) -> dict:
    """Decrypt and validate a stored retry payload."""

    if retry_cipher is None:
        raise RuntimeError(
            "WhatsApp retry encryption key is not configured."
        )

    try:
        decrypted = retry_cipher.decrypt(
            encrypted_payload.encode("utf-8")
        )

        payload = json.loads(decrypted.decode("utf-8"))

        if not isinstance(payload, dict):
            raise ValueError("Invalid retry payload format.")

        return payload

    except (InvalidToken, UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError(
            "Retry payload could not be decrypted or validated."
        )
# --------------------------------------------------
# WEBHOOK VERIFICATION
# --------------------------------------------------

@router.get("/webhook")
async def verify_webhook(request: Request):

    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(challenge or "")

    return PlainTextResponse(
        "Verification failed",
        status_code=403,
    )


# --------------------------------------------------
# SEND WHATSAPP TEXT MESSAGE
# --------------------------------------------------

def send_whatsapp_message(to: str, message: str):

    if not ACCESS_TOKEN or not PHONE_NUMBER_ID:
        raise RuntimeError(
            "WhatsApp API credentials are missing."
        )

    url = (
        f"https://graph.facebook.com/"
        f"{API_VERSION}/{PHONE_NUMBER_ID}/messages"
    )

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": message[:4000],
        },
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:

            result = json.loads(
                response.read().decode("utf-8")
            )

            logger.info(
                "WhatsApp message sent successfully."
            )

            return result

    except urllib.error.HTTPError as exc:

        error_body = exc.read().decode(
            "utf-8",
            errors="replace",
        )

        logger.error(
            "WhatsApp API error: HTTP %s - %s",
            exc.code,
            error_body,
        )

        raise


# --------------------------------------------------
# GET WHATSAPP MEDIA DOWNLOAD URL
# --------------------------------------------------

def get_whatsapp_media_url(media_id: str) -> str:

    if not ACCESS_TOKEN:
        raise RuntimeError(
            "WhatsApp access token is missing."
        )

    url = (
        f"https://graph.facebook.com/"
        f"{API_VERSION}/{media_id}"
    )

    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {ACCESS_TOKEN}",
        },
        method="GET",
    )

    with urllib.request.urlopen(req, timeout=30) as response:

        result = json.loads(
            response.read().decode("utf-8")
        )

    media_url = result.get("url")

    if not media_url:
        raise RuntimeError(
            "Meta did not return a media download URL."
        )

    # Only allow official Meta media hosts.
    parsed_url = urlparse(media_url)

    if (
        parsed_url.scheme != "https"
        or parsed_url.hostname not in ALLOWED_MEDIA_HOSTS
    ):
        raise RuntimeError(
            "Unexpected WhatsApp media download host."
        )

    return media_url


# --------------------------------------------------
# DOWNLOAD WHATSAPP DOCUMENT
# --------------------------------------------------

def download_whatsapp_document(
    media_id: str,
    filename: str,
) -> bytes:

    original_filename = Path(filename).name

    if not original_filename:
        raise ValueError(
            "Document filename is missing."
        )

    extension = Path(original_filename).suffix.lower()

    if extension not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise ValueError(
            "Unsupported document format. Allowed formats: "
            + ", ".join(sorted(ALLOWED_DOCUMENT_EXTENSIONS))
        )

    media_url = get_whatsapp_media_url(media_id)

    req = urllib.request.Request(
        media_url,
        headers={
            "Authorization": f"Bearer {ACCESS_TOKEN}",
        },
        method="GET",
    )

    with urllib.request.urlopen(req, timeout=60) as response:

        content_length = response.headers.get("Content-Length")

        if (
            content_length
            and int(content_length) > MAX_UPLOAD_BYTES
        ):
            raise ValueError(
                f"Document exceeds {MAX_UPLOAD_SIZE_MB} MB."
            )

        content = response.read(MAX_UPLOAD_BYTES + 1)

    if not content:
        raise ValueError(
            "Downloaded document is empty."
        )

    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError(
            f"Document exceeds {MAX_UPLOAD_SIZE_MB} MB."
        )

    return content


# --------------------------------------------------
# PROCESS INCOMING WHATSAPP DOCUMENT
# --------------------------------------------------


def process_incoming_document(
    sender: str,
    media_id: str,
    filename: str,
    user_id: int,
    message_id: str | None = None,
):
    destination = None

    try:
        original_filename = Path(filename).name

        user_directory = SAMPLE_DOCUMENTS_DIR / str(user_id)
        user_directory.mkdir(parents=True, exist_ok=True)

        # Generate a deterministic filename for retry operations.
        if message_id:
            message_key = hashlib.sha256(
                message_id.encode("utf-8")
            ).hexdigest()[:24]

            stored_filename = (
                f"wa_{message_key}_{original_filename}"
            )
        else:
            stored_filename = (
                f"{uuid.uuid4().hex}_{original_filename}"
            )

        destination = user_directory / stored_filename

        # Reuse the existing local document during retries.
        if destination.exists() and destination.is_file():
            logger.info(
                "Reusing cached WhatsApp document for user ID %s.",
                user_id,
            )

        else:
            logger.info(
                "Downloading WhatsApp document: %s",
                original_filename,
            )

            content = download_whatsapp_document(
                media_id=media_id,
                filename=original_filename,
            )

            destination.write_bytes(content)

        logger.info(
            "Document saved for application user ID %s.",
            user_id,
        )

        # Reuse existing ingestion pipeline.
        result = ingest_file(destination)

        if result.get("status") != "processed":
            raise ValueError(
                "No readable text was extracted from this document."
            )

        chunks = [
            {
                **chunk,
                "user_id": user_id,
            }
            for chunk in result.get("chunks", [])
        ]

        if not chunks:
            raise ValueError(
                "No text chunks could be created from this document."
            )

        # Reuse existing FAISS indexing.
        indexed_count = vector_store.add_chunks(chunks)

        if indexed_count == 0:
            raise RuntimeError(
                "Document chunks could not be indexed."
            )

        logger.info(
            "WhatsApp document indexed successfully. "
            "User ID: %s, chunks: %s",
            user_id,
            indexed_count,
        )

        send_whatsapp_message(
            sender,
            (
                "Document uploaded successfully!\n\n"
                f"File: {original_filename}\n"
                f"Chunks indexed: {indexed_count}\n\n"
                "You can now ask questions about this document "
                "directly in this WhatsApp chat."
            ),
        )

        return True

    except Exception as exc:
        logger.exception(
            "WhatsApp document processing failed."
        )

        try:
            send_whatsapp_message(
                sender,
                (
                    "Sorry, I could not process your document.\n\n"
                    f"Reason: {str(exc)[:500]}\n\n"
                    "Please check the file format and try again."
                ),
            )

        except Exception:
            logger.exception(
                "Could not send document upload error response."
            )

        return False



def process_tracked_incoming_document(
    message_id: str,
    sender: str,
    media_id: str,
    filename: str,
    user_id: int,
):
    """Track document processing and record failures."""

    try:
        update_whatsapp_message_status(
            message_id,
            "processing",
        )
    except Exception:
        logger.exception(
            "Could not mark WhatsApp document as processing."
        )
        return

    try:
        success = process_incoming_document(
            sender,
            media_id,
            filename,
            user_id,
            message_id=message_id,
        )

    except Exception as exc:
        logger.exception(
            "Tracked WhatsApp document processing failed."
        )

        success = False
        error = str(exc)

    else:
        error = (
            "Document processing or reply delivery failed."
        )

    try:
        if success:
            update_whatsapp_message_status(
                message_id,
                "processed",
            )
        else:
            update_whatsapp_message_status(
                message_id,
                "failed",
                error=error,
                increment_retry=True,
            )

    except Exception:
        logger.exception(
            "Could not record WhatsApp document processing result."
        )

# --------------------------------------------------
# PROCESS INCOMING WHATSAPP TEXT QUESTION
# --------------------------------------------------


def process_incoming_message(
    sender: str,
    question: str,
    user_id: int,
):
    """Answer a WhatsApp question using the linked user's documents."""

    db: Session = SessionLocal()

    try:
        conversation_id = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"ai-query-whatsapp:{sender}",
            )
        )

        logger.info(
            "Processing WhatsApp question for linked user ID %s.",
            user_id,
        )

        result = answer_query(
            question=question,
            conversation_id=conversation_id,
            user_id=user_id,
            db=db,
        )

        answer = result.get(
            "answer",
            "I could not generate an answer.",
        )

        if not answer:
            answer = (
                "I couldn't find relevant information "
                "in your indexed documents."
            )

        send_whatsapp_message(
            to=sender,
            message=str(answer),
        )
        return True

    except Exception:
        logger.exception("WhatsApp question processing failed.")

        try:
            send_whatsapp_message(
                sender,
                (
                    "Sorry, I encountered an error while "
                    "processing your question. Please try again."
                ),
            )
        except Exception:
            logger.exception(
                "Could not send WhatsApp error response."
            )
        return False

    finally:
        db.close()


def process_tracked_incoming_message(
    message_id: str,
    sender: str,
    question: str,
    user_id: int,
):
    """Track text-message processing and record failures."""

    try:
        update_whatsapp_message_status(
            message_id,
            "processing",
        )
    except Exception:
        logger.exception(
            "Could not mark WhatsApp text message as processing."
        )
        return

    try:
        success = process_incoming_message(
            sender,
            question,
            user_id,
        )
    except Exception as exc:
        logger.exception(
            "Tracked WhatsApp text processing failed."
        )

        success = False
        error = str(exc)

    else:
        error = (
            "Text message processing or reply delivery failed."
        )

    try:
        if success:
            update_whatsapp_message_status(
                message_id,
                "processed",
            )
        else:
            update_whatsapp_message_status(
                message_id,
                "failed",
                error=error,
                increment_retry=True,
            )

    except Exception:
        logger.exception(
            "Could not record WhatsApp text processing result."
        )

# --------------------------------------------------
# RECEIVE WHATSAPP WEBHOOK
# --------------------------------------------------





@router.post("/webhook")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    # 1. Read the exact raw request body.
    try:
        raw_body = await request.body()
    except Exception:
        logger.exception(
            "Failed to read WhatsApp webhook request body."
        )
        return {"status": "invalid_payload"}

    # 2. Read Meta signature header.
    signature_header = request.headers.get(
        "X-Hub-Signature-256",
        "",
    )

    # 3. Diagnostic logging.
    # These logs never expose the actual App Secret or signature.
    logger.warning(
        "DIAGNOSTIC - Meta App Secret configured: %s",
        bool(APP_SECRET),
    )

    logger.warning(
        "DIAGNOSTIC - Meta signature header received: %s",
        bool(signature_header),
    )

    logger.warning(
        "DIAGNOSTIC - WhatsApp webhook raw body length: %s",
        len(raw_body),
    )

    # 4. Verify Meta signature.
    if not verify_meta_signature(request, raw_body):
        logger.warning(
            "Rejected WhatsApp webhook: invalid Meta signature."
        )

        raise HTTPException(
            status_code=401,
            detail="Invalid webhook signature.",
        )

    logger.warning(
        "WhatsApp webhook signature verification successful."
    )

    # 5. Parse JSON after signature verification.
    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.warning(
            "WhatsApp webhook received invalid JSON."
        )
        return {"status": "invalid_payload"}

    if not isinstance(payload, dict):
        return {"status": "invalid_payload"}

    if payload.get("object") != "whatsapp_business_account":
        return {"status": "ignored"}

    for entry in payload.get("entry", []):
        if not isinstance(entry, dict):
            continue

        for change in entry.get("changes", []):
            if not isinstance(change, dict):
                continue

            value = change.get("value", {})

            if not isinstance(value, dict):
                continue

            for message in value.get("messages", []):
                if not isinstance(message, dict):
                    continue

                sender = "".join(
                    filter(
                        str.isdigit,
                        message.get("from", ""),
                    )
                )

                if not sender:
                    continue

                # 6. Validate Meta message ID.
                message_id = message.get("id")

                if (
                    not isinstance(message_id, str)
                    or not message_id.strip()
                ):
                    logger.warning(
                        "WhatsApp message rejected: missing message ID."
                    )
                    continue

                message_type = message.get("type")

                # 7. Handle LINK command separately.
                if message_type == "text":
                    question = (
                        message.get("text", {})
                        .get("body", "")
                        .strip()
                    )

                    link_match = re.fullmatch(
                        r"LINK\s+(\d{8})",
                        question,
                        flags=re.IGNORECASE,
                    )

                    if link_match:
                        if not register_whatsapp_message(message_id):
                            continue

                        background_tasks.add_task(
                            process_link_message,
                            sender,
                            link_match.group(1),
                        )
                        continue

                # 8. Resolve sender to their application account.
                user_id = get_linked_user_id(sender)

                if user_id is None:
                    if not register_whatsapp_message(message_id):
                        continue

                    background_tasks.add_task(
                        send_whatsapp_message,
                        sender,
                        (
                            "Your WhatsApp number is not linked to an "
                            "application account.\n\n"
                            "1. Log in to the AI Query Resolution System.\n"
                            "2. Generate a WhatsApp linking code from "
                            "your account.\n"
                            "3. Send LINK followed by the 8-digit code "
                            "here.\n\n"
                            "Example: LINK 12345678\n"
                            "The code expires after 10 minutes."
                        ),
                    )
                    continue

                # 9. Handle document messages.
                if message_type == "document":
                    document = message.get("document", {})

                    media_id = document.get("id")
                    filename = document.get("filename")

                    if not media_id or not filename:
                        if not register_whatsapp_message(message_id):
                            continue

                        logger.warning(
                            "WhatsApp document is missing "
                            "media ID or filename."
                        )

                        background_tasks.add_task(
                            send_whatsapp_message,
                            sender,
                            (
                                "I couldn't identify that document. "
                                "Please send it again with a filename."
                            ),
                        )
                        continue

                    retry_payload = {
                        "type": "document",
                        "sender": sender,
                        "user_id": user_id,
                        "media_id": media_id,
                        "filename": filename,
                    }

                    if not register_whatsapp_message(
                        message_id,
                        retry_payload,
                    ):
                        continue

                    logger.info(
                        "Incoming WhatsApp document received: %s",
                        filename,
                    )

                    background_tasks.add_task(
                        process_tracked_incoming_document,
                        message_id,
                        sender,
                        media_id,
                        filename,
                        user_id,
                    )

                # 10. Handle text questions.
                elif message_type == "text":
                    question = (
                        message.get("text", {})
                        .get("body", "")
                        .strip()
                    )

                    if not question:
                        if not register_whatsapp_message(message_id):
                            continue
                        continue

                    retry_payload = {
                        "type": "text",
                        "sender": sender,
                        "user_id": user_id,
                        "question": question,
                    }

                    if not register_whatsapp_message(
                        message_id,
                        retry_payload,
                    ):
                        continue

                    logger.info(
                        "Incoming WhatsApp text message received "
                        "from a linked account."
                    )

                    background_tasks.add_task(
                        process_tracked_incoming_message,
                        message_id,
                        sender,
                        question,
                        user_id,
                    )

                # 11. Unsupported message type.
                else:
                    if not register_whatsapp_message(message_id):
                        continue

                    background_tasks.add_task(
                        send_whatsapp_message,
                        sender,
                        (
                            "Please send a supported document "
                            "(PDF, DOCX, TXT, MD or CSV), "
                            "or type a question about your documents."
                        ),
                    )

    return {"status": "received"}
