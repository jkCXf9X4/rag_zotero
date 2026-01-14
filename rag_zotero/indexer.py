from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib

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


def index_files(
    *,
    files: list[Path],
    chroma_dir: Path,
    collection_name: str,
    embedder,
    chunk_size: int,
    chunk_overlap: int,
) -> list[IndexedFile]:
    collection = get_collection(chroma_dir=chroma_dir, name=collection_name)

    out: list[IndexedFile] = []
    for path in files:
        pages, _full = extract_any(path)

        ids: list[str] = []
        docs: list[str] = []
        metas: list[dict] = []

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
                    }
                )

        if not docs:
            out.append(IndexedFile(path=path, chunks_added=0))
            continue

        embeddings = embedder.embed_texts(docs)
        collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embeddings)
        out.append(IndexedFile(path=path, chunks_added=len(docs)))

    return out

