
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Configurable directories:
# Local development uses project folders.
# Render can use a persistent disk mounted at /var/data.
DATA_DIR = Path(
    os.getenv("APP_DATA_DIR", str(PROJECT_ROOT / "data"))
)

STORAGE_DIR = Path(
    os.getenv("APP_STORAGE_DIR", str(PROJECT_ROOT / "storage"))
)

SAMPLE_DOCUMENTS_DIR = DATA_DIR / "sample_documents"
PROCESSED_DIR = DATA_DIR / "processed"

MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "15"))

ALLOWED_DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".txt",
    ".md",
    ".csv",
}

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "120"))

for directory in (
    SAMPLE_DOCUMENTS_DIR,
    PROCESSED_DIR,
    STORAGE_DIR,
):
    directory.mkdir(parents=True, exist_ok=True)
