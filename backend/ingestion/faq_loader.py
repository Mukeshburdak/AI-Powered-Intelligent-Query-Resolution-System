import csv
from pathlib import Path

def load_faq_csv(path: str | Path) -> list[dict[str, str]]:
    """Load a FAQ CSV containing at least 'question' and 'answer' columns."""
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"question", "answer"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError("FAQ CSV must contain 'question' and 'answer' columns.")
        return [
            {"question": (row.get("question") or "").strip(),
             "answer": (row.get("answer") or "").strip()}
            for row in reader
            if (row.get("question") or "").strip() and (row.get("answer") or "").strip()
        ]
