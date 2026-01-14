from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

import os


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


class AppConfig(BaseModel):
    chroma_dir: str = os.getenv("CHROMA_DIR", "./data/chroma")
    chroma_collection: str = os.getenv("CHROMA_COLLECTION", "zotero")

    openai_api_key: str | None = os.getenv("OPENAI_API_KEY") or None
    openai_embed_model: str = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

    chunk_size: int = _env_int("CHUNK_SIZE", 1200)
    chunk_overlap: int = _env_int("CHUNK_OVERLAP", 200)

    def chroma_path(self) -> Path:
        return Path(self.chroma_dir).expanduser().resolve()


@dataclass(frozen=True)
class RuntimeInfo:
    python: str
    chroma_dir: str
    chroma_collection: str
    embeddings_backend: str


def load_config() -> AppConfig:
    load_dotenv(override=False)
    return AppConfig()

