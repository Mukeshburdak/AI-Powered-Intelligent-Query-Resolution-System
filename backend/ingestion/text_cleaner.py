import re


def clean_text(text: str) -> str:
    """Normalize extracted document text before chunking."""
    if not text:
        return ""

    text = text.replace("\x00", " ")

    text = text.replace("\r\n", "\n").replace("\r", "\n")

    text = re.sub(r"[ \t]+", " ", text)

    text = "\n".join(line.strip() for line in text.split("\n"))

    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()