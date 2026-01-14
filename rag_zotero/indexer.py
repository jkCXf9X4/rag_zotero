from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
from collections.abc import Callable

from .extract import extract_any
from .text_chunking import chunk_text
from .vectorstore import get_collection


@dataclass(frozen=True)
class IndexedFile:
    path: Path
    chunks_added: int


def _chunk_id(*, source_path: str, page: int, chunk_index: int) -> str:
    raw = f"{source_path}::p{page}::c{chunk_index}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()


def index_file(
    *,
    path: Path,
    collection,
    embedder,
    chunk_size: int,
    chunk_overlap: int,
    extra_metadata: dict | None = None,
    status: Callable[[str], None] | None = None,
) -> IndexedFile:
    if status:
        status("Extracting text")
    pages, _full = extract_any(path)

    ids: list[str] = []
    docs: list[str] = []
    metas: list[dict] = []

    if status:
        status("Chunking")
    for page in pages:
        chunks = chunk_text(page.text, chunk_size=chunk_size, overlap=chunk_overlap)
        for chunk_index, chunk in enumerate(chunks):
            ids.append(
                _chunk_id(
                    source_path=str(path),
                    page=page.page_number,
                    chunk_index=chunk_index,
                )
            )
            docs.append(chunk)
            metas.append(
                {
                    "source_path": str(path),
                    "page": page.page_number,
                    "chunk": chunk_index,
                    **(extra_metadata or {}),
                }
            )

    if not docs:
        if status:
            status("No extractable text; skipped")
        return IndexedFile(path=path, chunks_added=0)

    if status:
        status(f"Embedding {len(docs)} chunks")
    embeddings = embedder.embed_texts(docs)

    if status:
        status("Upserting into Chroma")
    collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embeddings)
    return IndexedFile(path=path, chunks_added=len(docs))


def index_files(
    *,
    files: list[Path],
    chroma_dir: Path,
    collection_name: str,
    embedder,
    chunk_size: int,
    chunk_overlap: int,
    status: Callable[[Path, str], None] | None = None,
) -> list[IndexedFile]:
    collection = get_collection(chroma_dir=chroma_dir, name=collection_name)

    out: list[IndexedFile] = []
    for path in files:
        per_file_status = None
        if status:
            per_file_status = lambda msg, p=path: status(p, msg)
        out.append(
            index_file(
                path=path,
                collection=collection,
                embedder=embedder,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                status=per_file_status,
            )
        )

    return out
