def chunk_text(text: str, chunk_size: int = 3000, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks. Tries to break at sentence boundaries."""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            # Try to break at a natural boundary (space/newline) within last 200 chars
            boundary = text.rfind(' ', end - 200, end)
            if boundary == -1:
                boundary = text.rfind('\n', end - 200, end)
            if boundary != -1:
                end = boundary
        chunks.append(text[start:end].strip())
        start = end - overlap
    return [c for c in chunks if c]
