from backend.config import CHUNK_OVERLAP, CHUNK_SIZE


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """
    Split text into overlapping chunks.

    Prefer paragraph, sentence, and word boundaries where possible.
    Chunk size and overlap are measured in characters.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")

    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)

        if end < text_length:
            minimum_boundary = start + int(chunk_size * 0.6)
            candidates = [
                text.rfind("\n\n", minimum_boundary, end),
                text.rfind(". ", minimum_boundary, end),
                text.rfind("? ", minimum_boundary, end),
                text.rfind("! ", minimum_boundary, end),
                text.rfind(" ", minimum_boundary, end),
            ]

            boundary = max(candidates)

            if boundary > start:
                end = boundary + (1 if text[boundary:boundary + 1] == " " else 0)

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        next_start = end - overlap
        if next_start <= start:
            next_start = end

        start = next_start

    return chunks