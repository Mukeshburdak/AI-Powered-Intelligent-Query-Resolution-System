
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.config import (
    ALLOWED_DOCUMENT_EXTENSIONS,
    MAX_UPLOAD_SIZE_MB,
    SAMPLE_DOCUMENTS_DIR,
)
from backend.database.models import User
from backend.ingestion.ingestion_pipeline import ingest_file
from backend.retrieval.vector_store import vector_store
from backend.security.auth import get_current_user

router = APIRouter(tags=["documents"])


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    original_filename = Path(file.filename or "").name
    suffix = Path(original_filename).suffix.lower()

    if not original_filename or suffix not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported file type. Allowed: "
                f"{', '.join(sorted(ALLOWED_DOCUMENT_EXTENSIONS))}"
            ),
        )

    content = await file.read()
    max_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024

    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {MAX_UPLOAD_SIZE_MB} MB limit.",
        )

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty.",
        )

    # Each user gets a separate upload directory.
    user_directory = SAMPLE_DOCUMENTS_DIR / str(current_user.id)
    user_directory.mkdir(parents=True, exist_ok=True)

    # Unique stored filename prevents accidental overwriting.
    stored_filename = f"{uuid.uuid4().hex}_{original_filename}"
    destination = user_directory / stored_filename

    destination.write_bytes(content)

    try:
        result = ingest_file(destination)

        chunks = [
        {
           **chunk,
           "user_id": current_user.id,
        }
        for chunk in result.get("chunks", [])
        ]

        indexed_count = vector_store.add_chunks(chunks)

        return {
            "message": "File uploaded and processed",
            "uploaded_by": current_user.email,
            "document_id": stored_filename,
            "original_filename": original_filename,
            "stored_filename": stored_filename,
            **result,
            "indexed_chunks": indexed_count,
        }

    except Exception as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {str(exc)}",
        )

@router.get("/documents")
def list_uploaded_documents(
    current_user: User = Depends(get_current_user),
):
    """List documents uploaded by the authenticated user."""

    user_directory = SAMPLE_DOCUMENTS_DIR / str(current_user.id)

    if not user_directory.exists():
        return {"documents": []}

    documents = []

    for file_path in user_directory.iterdir():
        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in ALLOWED_DOCUMENT_EXTENSIONS:
            continue

        stored_filename = file_path.name

        # Remove the UUID prefix to recover the original filename.
        _, separator, original_filename = stored_filename.partition("_")

        if not separator or not original_filename:
            original_filename = stored_filename

        documents.append({
            "document_id": stored_filename,
            "original_filename": original_filename,
            "file_type": file_path.suffix.lower(),
            "size_bytes": file_path.stat().st_size,
        })

    documents.sort(
        key=lambda item: item["original_filename"].lower()
    )

    return {"documents": documents}
