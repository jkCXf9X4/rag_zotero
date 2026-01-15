from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from pydantic import BaseModel, Field

import os


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


class AppConfig(BaseModel):
    chroma_dir: str = Field(default_factory=lambda: os.getenv("CHROMA_DIR", "./data/chroma"))
    chroma_collection: str = Field(default_factory=lambda: os.getenv("CHROMA_COLLECTION", "zotero"))

    openai_api_key: str | None = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY") or None)
    openai_embed_model: str = Field(
        default_factory=lambda: os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
    )

    openrouter_api_key: str | None = Field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY") or None)
    openrouter_eval_model: str = Field(
        default_factory=lambda: os.getenv("OPENROUTER_EVAL_MODEL", "openai/gpt-4o-mini")
    )

    chunk_size: int = Field(default_factory=lambda: _env_int("CHUNK_SIZE", 1200))
    chunk_overlap: int = Field(default_factory=lambda: _env_int("CHUNK_OVERLAP", 200))

    def chroma_path(self) -> Path:
        return Path(self.chroma_dir).expanduser().resolve()


@dataclass(frozen=True)
class RuntimeInfo:
    python: str
    chroma_dir: str
    chroma_collection: str
    embeddings_backend: str


def load_config() -> AppConfig:
    dotenv_override = os.getenv("RAG_ZOTERO_DOTENV_OVERRIDE", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
    }
    dotenv_path = os.getenv("RAG_ZOTERO_ENV_FILE") or find_dotenv(usecwd=True)
    if dotenv_path:
        load_dotenv(dotenv_path=dotenv_path, override=dotenv_override)
    else:
        load_dotenv(override=dotenv_override)
    return AppConfig()
