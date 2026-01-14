from __future__ import annotations

from pathlib import Path
import sys

import typer
from rich.console import Console
from rich.table import Table

from .config import load_config
from .embeddings import resolve_embeddings
from .indexer import index_files
from .vectorstore import get_collection, query_collection
from .zotero_scan import scan_storage


app = typer.Typer(no_args_is_help=True)
console = Console()


def _as_path(p: str | None) -> Path | None:
    if not p:
        return None
    return Path(p).expanduser()


@app.command()
def doctor(
    live: bool = typer.Option(
        False, help="Run a live embedding request (may download models / call APIs)"
    )
) -> None:
    cfg = load_config()
    chroma_dir = cfg.chroma_path()

    try:
        embedder, backend = resolve_embeddings(
            openai_api_key=cfg.openai_api_key,
            openai_model=cfg.openai_embed_model,
        )
        embed_ok = True
        if live:
            _ = embedder.embed_query("ping")
    except Exception as exc:
        backend = "unavailable"
        embed_ok = False
        console.print(f"[yellow]Embeddings not ready:[/yellow] {exc}")

    table = Table(title="rag-zotero doctor")
    table.add_column("Key")
    table.add_column("Value")
    table.add_row("Python", sys.version.split()[0])
    table.add_row("Chroma dir", str(chroma_dir))
    table.add_row("Collection", cfg.chroma_collection)
    table.add_row("Embeddings", backend)
    table.add_row("Embeddings OK", str(embed_ok))
    console.print(table)


@app.command()
def scan(
    storage_dir: str = typer.Option(..., help="Path to Zotero storage/ folder"),
    limit: int = typer.Option(50, help="Max files to print"),
) -> None:
    files = scan_storage(_as_path(storage_dir) or Path(storage_dir))
    console.print(f"Found {len(files)} files")
    for p in files[: max(0, limit)]:
        console.print(str(p))


@app.command()
def index(
    storage_dir: str = typer.Option(..., help="Path to Zotero storage/ folder"),
    limit: int | None = typer.Option(None, help="Index only first N files (debug)"),
) -> None:
    cfg = load_config()
    embedder, backend = resolve_embeddings(
        openai_api_key=cfg.openai_api_key,
        openai_model=cfg.openai_embed_model,
    )
    console.print(f"Embeddings backend: {backend}")

    files = scan_storage(_as_path(storage_dir) or Path(storage_dir))
    if limit is not None:
        files = files[: max(0, int(limit))]

    results = index_files(
        files=files,
        chroma_dir=cfg.chroma_path(),
        collection_name=cfg.chroma_collection,
        embedder=embedder,
        chunk_size=cfg.chunk_size,
        chunk_overlap=cfg.chunk_overlap,
    )
    total_chunks = sum(r.chunks_added for r in results)
    console.print(f"Indexed {len(results)} files, added {total_chunks} chunks")


@app.command()
def query(
    q: str = typer.Argument(..., help="Query text"),
    n: int = typer.Option(5, help="Number of results"),
) -> None:
    cfg = load_config()
    embedder, backend = resolve_embeddings(
        openai_api_key=cfg.openai_api_key,
        openai_model=cfg.openai_embed_model,
    )

    collection = get_collection(chroma_dir=cfg.chroma_path(), name=cfg.chroma_collection)
    q_emb = embedder.embed_query(q)
    results = query_collection(collection, q_emb, n_results=n)

    console.print(f"Embeddings backend: {backend}")
    if not results:
        console.print("No results.")
        raise typer.Exit(code=0)

    table = Table(title="Top matches")
    table.add_column("Score", justify="right")
    table.add_column("Source")
    table.add_column("Page", justify="right")
    table.add_column("Snippet")
    for r in results:
        source = str(r.metadata.get("source_path", ""))
        page = str(r.metadata.get("page", ""))
        snippet = r.document.replace("\n", " ").strip()
        if len(snippet) > 160:
            snippet = snippet[:157] + "..."
        table.add_row(f"{r.score:.3f}", source, page, snippet)
    console.print(table)
