from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
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
    model_name: str

    def _model(self):
        from sentence_transformers import SentenceTransformer

        try:
            return SentenceTransformer(self.model_name)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load local embedding model '{self.model_name}'. "
                "This usually means the model is not cached and the Hugging Face download "
                "failed. Set SENTENCE_TRANSFORMERS_MODEL in .env to choose a different local "
                "model. If this machine uses a corporate TLS proxy, set SSL_CERT_FILE to the "
                "appropriate CA bundle. Otherwise, set OPENAI_API_KEY to use OpenAI embeddings."
            ) from exc

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        model = self._model()
        vectors = model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vectors]

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]


def resolve_embeddings(
    *,
    openai_api_key: str | None,
    openai_model: str,
    sentence_transformers_model: str,
):
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
    return (
        SentenceTransformersEmbeddings(
            model_name=_resolve_sentence_transformers_model(sentence_transformers_model)
        ),
        "sentence-transformers",
    )


def _resolve_sentence_transformers_model(model_spec: str) -> str:
    candidate = Path(model_spec).expanduser()
    if candidate.exists():
        if not candidate.is_dir():
            raise RuntimeError(
                f"Local embedding model path '{candidate}' must be a directory produced by "
                "a Sentence Transformers download."
            )
        return str(candidate.resolve())
    return model_spec
