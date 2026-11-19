
import csv
from pathlib import Path

from pypdf import PdfReader
from docx import Document


def load_document(path: str | Path) -> str:
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix == ".txt":
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    if suffix == ".md":
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    if suffix == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )

    if suffix == ".docx":
        document = Document(str(path))
        return "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
        )

    if suffix == ".csv":
        return load_csv(path)

    raise ValueError(
        f"Unsupported document type: {suffix}"
    )


def load_csv(path: Path) -> str:
    """Convert CSV rows into readable text for RAG indexing."""

    rows_as_text = []

    # utf-8-sig handles CSV files saved with a BOM.
    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as csv_file:

        sample = csv_file.read(4096)
        csv_file.seek(0)

        try:
            dialect = csv.Sniffer().sniff(
                sample,
                delimiters=",;\t|",
            )
        except csv.Error:
            dialect = csv.excel

        reader = csv.DictReader(
            csv_file,
            dialect=dialect,
        )

        if not reader.fieldnames:
            return ""

        headers = [
            str(header).strip()
            for header in reader.fieldnames
            if header is not None
        ]

        for row_number, row in enumerate(reader, start=1):
            values = []

            for header in headers:
                value = row.get(header, "")
                values.append(
                    f"{header}: {str(value or '').strip()}"
                )

            rows_as_text.append(
                f"Row {row_number}: "
                + "; ".join(values)
            )

    return "\n".join(rows_as_text)
