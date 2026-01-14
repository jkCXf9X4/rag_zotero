from __future__ import annotations


def chunk_text(text: str, *, chunk_size: int, overlap: int) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    if chunk_size <= 0:
        return [text]
    if overlap < 0:
        overlap = 0
    if overlap >= chunk_size:
        overlap = max(0, chunk_size // 4)

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks

