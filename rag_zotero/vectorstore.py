from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SearchResult:
    id: str
    score: float
    document: str
    metadata: dict[str, Any]


def get_collection(*, chroma_dir: Path, name: str):
    import chromadb

    chroma_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_dir))
    return client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})


def query_collection(collection, query_embedding: list[float], *, n_results: int) -> list[SearchResult]:
    res = collection.query(query_embeddings=[query_embedding], n_results=n_results)
    ids = (res.get("ids") or [[]])[0]
    docs = (res.get("documents") or [[]])[0]
    metadatas = (res.get("metadatas") or [[]])[0]
    distances = (res.get("distances") or [[]])[0]

    out: list[SearchResult] = []
    for i in range(len(ids)):
        distance = float(distances[i]) if distances and distances[i] is not None else 0.0
        score = 1.0 - distance
        out.append(
            SearchResult(
                id=str(ids[i]),
                score=score,
                document=str(docs[i]),
                metadata=dict(metadatas[i] or {}),
            )
        )
    return out

