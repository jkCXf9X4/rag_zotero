from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class Embeddings(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, query: str) -> list[float]: ...


@dataclass
class OpenAIEmbeddings:
    api_key: str
    model: str

    def _client(self):
        from openai import OpenAI

        return OpenAI(api_key=self.api_key)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        client = self._client()
        resp = client.embeddings.create(model=self.model, input=texts)
        return [d.embedding for d in resp.data]

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]


@dataclass
class SentenceTransformersEmbeddings:
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"

    def _model(self):
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(self.model_name)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        model = self._model()
        vectors = model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vectors]

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]


def resolve_embeddings(*, openai_api_key: str | None, openai_model: str):
    if openai_api_key:
        return OpenAIEmbeddings(api_key=openai_api_key, model=openai_model), "openai"

    try:
        import sentence_transformers  # noqa: F401
    except Exception as exc:
        raise RuntimeError(
            "No embeddings backend configured.\n"
            "- Option A (recommended): set OPENAI_API_KEY in .env\n"
            "- Option B (local): `pip install -e '.[local-embeddings]'`\n"
        ) from exc
    return SentenceTransformersEmbeddings(), "sentence-transformers"

