from __future__ import annotations

from pathlib import Path


DEFAULT_EXTENSIONS = {".pdf", ".txt", ".md"}


def scan_storage(storage_dir: Path, *, extensions: set[str] | None = None) -> list[Path]:
    storage_dir = storage_dir.expanduser().resolve()
    if not storage_dir.exists():
        raise FileNotFoundError(storage_dir)
    if not storage_dir.is_dir():
        raise NotADirectoryError(storage_dir)

    exts = {e.lower() for e in (extensions or DEFAULT_EXTENSIONS)}
    results: list[Path] = []
    for path in storage_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in exts:
            results.append(path)
    results.sort()
    return results

