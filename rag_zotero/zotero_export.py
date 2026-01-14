from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
from typing import Any


_YEAR_RE = re.compile(r"(?P<year>\d{4})")


@dataclass(frozen=True)
class ZoteroItem:
    key: str
    item_type: str
    title: str | None
    creators: list[str]
    year: int | None
    doi: str | None
    url: str | None
    citekey: str | None


@dataclass(frozen=True)
class ZoteroExportIndex:
    items_by_key: dict[str, ZoteroItem]
    attachment_to_parent: dict[str, str]  # attachmentKey -> parentItemKey

    def metadata_for_attachment(self, attachment_key: str) -> dict[str, Any]:
        meta: dict[str, Any] = {"attachment_key": attachment_key}
        parent_key = self.attachment_to_parent.get(attachment_key)
        if parent_key:
            meta["item_key"] = parent_key
        item = self.items_by_key.get(parent_key or "")
        if not item:
            return meta

        meta.update(
            {
                "title": item.title,
                "creators": item.creators,
                "year": item.year,
                "doi": item.doi,
                "url": item.url,
                "citekey": item.citekey,
            }
        )
        return meta


def _as_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        items = payload.get("items")
        if isinstance(items, list):
            return [x for x in items if isinstance(x, dict)]
    raise ValueError("Unsupported Zotero export structure (expected list or {'items': [...]})")


def _creator_to_str(c: dict[str, Any]) -> str | None:
    name = (c.get("name") or "").strip()
    if name:
        return name
    first = (c.get("firstName") or "").strip()
    last = (c.get("lastName") or "").strip()
    full = " ".join([p for p in [first, last] if p]).strip()
    return full or None


def _extract_year(raw: str | None) -> int | None:
    if not raw:
        return None
    m = _YEAR_RE.search(raw)
    if not m:
        return None
    try:
        return int(m.group("year"))
    except Exception:
        return None


def _attachment_key_from_path_field(path_field: str | None) -> str | None:
    if not path_field:
        return None
    # Common in Zotero exports: "storage:ABCD1234/foo.pdf"
    if path_field.startswith("storage:"):
        rest = path_field[len("storage:") :]
        key = rest.split("/", 1)[0].strip()
        return key or None
    return None


def load_zotero_export(path: Path) -> ZoteroExportIndex:
    payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    rows = _as_list(payload)

    items_by_key: dict[str, ZoteroItem] = {}
    attachment_to_parent: dict[str, str] = {}

    for row in rows:
        key = (row.get("key") or row.get("itemKey") or "").strip()
        if not key:
            continue

        item_type = str(row.get("itemType") or "").strip()
        title = row.get("title")
        if isinstance(title, str):
            title = title.strip() or None
        else:
            title = None

        creators_raw = row.get("creators")
        creators: list[str] = []
        if isinstance(creators_raw, list):
            for c in creators_raw:
                if isinstance(c, dict):
                    s = _creator_to_str(c)
                    if s:
                        creators.append(s)

        doi = row.get("DOI") or row.get("doi")
        doi = doi.strip() if isinstance(doi, str) and doi.strip() else None

        url = row.get("url") or row.get("URL")
        url = url.strip() if isinstance(url, str) and url.strip() else None

        citekey = row.get("citekey") or row.get("citationKey")
        citekey = citekey.strip() if isinstance(citekey, str) and citekey.strip() else None

        year = _extract_year(
            (row.get("date") if isinstance(row.get("date"), str) else None)
            or (row.get("issued") if isinstance(row.get("issued"), str) else None)
        )

        items_by_key[key] = ZoteroItem(
            key=key,
            item_type=item_type,
            title=title,
            creators=creators,
            year=year,
            doi=doi,
            url=url,
            citekey=citekey,
        )

        parent = (row.get("parentItem") or row.get("parentItemKey") or "").strip()
        if parent:
            attachment_to_parent[key] = parent
            continue

        # Some exports place attachment info differently.
        attachment_key = _attachment_key_from_path_field(
            row.get("path") if isinstance(row.get("path"), str) else None
        )
        if attachment_key:
            # If this row is a parent item with a path, we at least record the attachment key.
            # There may not be a reliable link to the parent; we leave it unattached.
            attachment_to_parent.setdefault(attachment_key, "")

    return ZoteroExportIndex(items_by_key=items_by_key, attachment_to_parent=attachment_to_parent)


def attachment_key_from_storage_path(*, file_path: Path, storage_dir: Path) -> str | None:
    try:
        rel = file_path.resolve().relative_to(storage_dir.expanduser().resolve())
    except Exception:
        return None
    parts = rel.parts
    if not parts:
        return None
    key = parts[0].strip()
    return key or None

