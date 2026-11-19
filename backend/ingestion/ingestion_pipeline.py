from pathlib import Path

from backend.config import PROCESSED_DIR
from backend.ingestion.chunker import chunk_text
from backend.ingestion.document_loader import load_document
from backend.ingestion.text_cleaner import clean_text


def ingest_file(path: str | Path) -> dict:
    """Extract, clean, chunk, and save a document's text."""
    path = Path(path)

    extracted_text = load_document(path)
    cleaned_text = clean_text(extracted_text)
    chunks = chunk_text(cleaned_text)

    output_path = PROCESSED_DIR / f"{path.stem}.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(cleaned_text, encoding="utf-8")

    chunk_metadata = [
        {
            "chunk_id": f"{path.stem}_{index:04d}",
            "source": path.name,
            "chunk_index": index,
            "text": chunk,
        }
        for index, chunk in enumerate(chunks)
    ]

    return {
        "filename": path.name,
        "characters": len(cleaned_text),
        "chunks_created": len(chunks),
        "chunks": chunk_metadata,
        "processed_text": str(output_path.relative_to(PROCESSED_DIR.parent.parent)),
        "status": "processed" if cleaned_text else "no_text_extracted",
    }