from __future__ import annotations

from pathlib import Path
import json
import sys

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from .config import load_config
from .embeddings import resolve_embeddings
from .indexer import index_file
from .vectorstore import get_collection, query_collection
from .zotero_scan import scan_storage
from .zotero_export import attachment_key_from_storage_path, load_zotero_export


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
    limit: int = typer.Option(1000, help="Max files to print"),
    export_json: str | None = typer.Option(
        None, help="Path to Zotero/BetterBibTeX JSON export for metadata"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON"),
) -> None:
    storage_path = _as_path(storage_dir) or Path(storage_dir)
    files = scan_storage(storage_path)

    export_index = None
    export_stats = None
    if export_json:
        export_index = load_zotero_export(Path(export_json).expanduser())
        export_stats = {
            "items": len(export_index.items_by_key),
            "attachment_links": len(export_index.attachment_to_parent),
        }

    if json_output:
        rows: list[dict] = []
        for p in files[: max(0, limit)]:
            akey = None
            meta = None
            if export_index:
                akey = attachment_key_from_storage_path(file_path=p, storage_dir=storage_path)
                meta = export_index.metadata_for_attachment(akey) if akey else None
            rows.append(
                {
                    "path": str(p),
                    "attachment_key": akey,
                    "metadata": meta or {},
                }
            )
        print(
            json.dumps(
                {
                    "storage_dir": str(storage_path),
                    "files_total": len(files),
                    "files": rows,
                    "export": export_stats or {},
                },
                ensure_ascii=False,
            )
        )
        return

    console.print(f"Found {len(files)} files")
    if export_stats:
        console.print(
            f"Loaded export: {export_stats['items']} items, {export_stats['attachment_links']} attachment links"
        )

        sample = files[: min(len(files), 50)]
        matched = 0
        for p in sample:
            akey = attachment_key_from_storage_path(file_path=p, storage_dir=storage_path)
            if not akey:
                continue
            meta = export_index.metadata_for_attachment(akey)
            if any(meta.get(k) for k in ("title", "year", "doi", "url", "citekey")):
                matched += 1
        if sample and matched == 0:
            console.print(
                "[yellow]No attachment metadata matched scanned files.[/yellow] "
                "Ensure you exported a full library as Zotero JSON or BetterBibTeX JSON "
                "(not CSL JSON/bibliography exports, which typically lack attachment keys)."
            )

    for p in files[: max(0, limit)]:
        if export_index:
            akey = attachment_key_from_storage_path(file_path=p, storage_dir=storage_path)
            meta = export_index.metadata_for_attachment(akey) if akey else {}
            title = meta.get("title") or ""
            year = meta.get("year") or ""
            citekey = meta.get("citekey") or ""
            suffix = " ".join([s for s in [str(year), str(citekey), str(title)] if str(s).strip()])
            if suffix:
                console.print(f"{suffix} [dim]'{p}'[/dim]")
            else:
                console.print(str(p))
        else:
            console.print(str(p))


@app.command()
def index(
    storage_dir: str = typer.Option(..., help="Path to Zotero storage/ folder"),
    limit: int | None = typer.Option(None, help="Index only first N files (debug)"),
    continue_on_error: bool = typer.Option(True, help="Continue if a file fails to index"),
    export_json: str | None = typer.Option(
        None, help="Path to Zotero/BetterBibTeX JSON export for metadata"
    ),
) -> None:
    cfg = load_config()
    embedder, backend = resolve_embeddings(
        openai_api_key=cfg.openai_api_key,
        openai_model=cfg.openai_embed_model,
    )
    console.print(f"Embeddings backend: {backend}")

    storage_path = _as_path(storage_dir) or Path(storage_dir)
    console.print("Scanning storage...")
    files = scan_storage(storage_path)
    if limit is not None:
        files = files[: max(0, int(limit))]
    console.print(f"Found {len(files)} files")
    if not files:
        raise typer.Exit(code=0)

    collection = get_collection(chroma_dir=cfg.chroma_path(), name=cfg.chroma_collection)

    export_index = None
    if export_json:
        console.print("Loading Zotero export metadata...")
        export_index = load_zotero_export(Path(export_json).expanduser())
        console.print(
            f"Loaded export: {len(export_index.items_by_key)} items, "
            f"{len(export_index.attachment_to_parent)} attachment links"
        )

    results = []
    failed = 0
    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Indexing", total=len(files))

        for path in files:
            progress.update(task, description=f"Indexing {path.name}")

            extra_metadata = None
            if export_index:
                akey = attachment_key_from_storage_path(file_path=path, storage_dir=storage_path)
                extra_metadata = export_index.metadata_for_attachment(akey) if akey else None

            def status(msg: str, p: Path = path) -> None:
                progress.console.log(f"[dim]{p.name}[/dim]: {msg}")

            try:
                results.append(
                    index_file(
                        path=path,
                        collection=collection,
                        embedder=embedder,
                        chunk_size=cfg.chunk_size,
                        chunk_overlap=cfg.chunk_overlap,
                        extra_metadata=extra_metadata,
                        status=status,
                    )
                )
            except Exception as exc:
                failed += 1
                progress.console.log(f"[red]{path.name}[/red]: failed ({exc})")
                if not continue_on_error:
                    raise
            finally:
                progress.advance(task)

    total_chunks = sum(r.chunks_added for r in results)
    console.print(
        f"Indexed {len(results)} files, added {total_chunks} chunks"
        + (f", {failed} failed" if failed else "")
    )


@app.command()
def query(
    q: str = typer.Argument(..., help="Query text"),
    n: int = typer.Option(7, help="Number of results"),
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON"),
) -> None:
    cfg = load_config()
    embedder, backend = resolve_embeddings(
        openai_api_key=cfg.openai_api_key,
        openai_model=cfg.openai_embed_model,
    )

    collection = get_collection(chroma_dir=cfg.chroma_path(), name=cfg.chroma_collection)
    q_emb = embedder.embed_query(q)
    results = query_collection(collection, q_emb, n_results=n)

    if json_output:
        print(
            json.dumps(
                {
                    "backend": backend,
                    "query": q,
                    "n": n,
                    "results": [
                        {
                            "score": r.score,
                            "title": r.metadata.get("title") or "",
                            "year": r.metadata.get("year") or "",
                            "source_path": r.metadata.get("source_path") or "",
                            "page": r.metadata.get("page") or "",
                            "text": (r.document or "").replace("\n", " ").strip(),
                            "metadata": r.metadata,
                        }
                        for r in results
                    ],
                },
                ensure_ascii=False,
            )
        )
        return

    console.print(f"Embeddings backend: {backend}")
    if not results:
        console.print("No results.")
        raise typer.Exit(code=0)

    table = Table(title="Top matches")
    table.add_column("Score", justify="right")
    table.add_column("Title")
    table.add_column("Year", justify="right")
    table.add_column("Source")
    table.add_column("Page", justify="right")
    table.add_column("Text")
    for r in results:
        title = r.metadata.get("title", '')
        creators = r.metadata.get("creators", '')
        title_text = f"{title}\nCreators: {creators}"
        year = str(r.metadata.get("year") or "")
        source = str(r.metadata.get("source_path", ""))
        page = str(r.metadata.get("page", ""))
        text = str((r.document or "").replace("\n", " ").strip())
        table.add_row(f"{r.score:.3f}", title_text, year, source, page, text)
    console.print(table)
