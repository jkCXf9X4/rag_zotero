from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PageText:
    page_number: int  # 1-based
    text: str


def extract_pdf_pages(path: Path) -> list[PageText]:
    try:
        import fitz  # PyMuPDF
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Missing dependency for PDF extraction. Install `pymupdf`."
        ) from exc

    pages: list[PageText] = []
    with fitz.open(str(path)) as doc:
        for i in range(doc.page_count):
            page = doc.load_page(i)
            text = page.get_text("text") or ""
            pages.append(PageText(page_number=i + 1, text=text))
    return pages


def extract_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def extract_any(path: Path) -> tuple[list[PageText], str]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        pages = extract_pdf_pages(path)
        full = "\n".join(p.text for p in pages)
        return pages, full
    if suffix in {".txt", ".md"}:
        text = extract_text_file(path)
        return [PageText(page_number=1, text=text)], text
    raise ValueError(f"Unsupported file type: {path}")

