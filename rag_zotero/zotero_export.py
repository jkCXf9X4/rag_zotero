from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
from typing import Any


_YEAR_RE = re.compile(r"(?P<year>\d{4})")
_ZOTERO_STORAGE_KEY_RE = re.compile(r"(?:^|[\\\\/])storage[\\\\/](?P<key>[A-Z0-9]{8})(?:[\\\\/]|$)")


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

        creators = "; ".join([c for c in item.creators if str(c).strip()]).strip() or None
        meta.update(
            {
                "title": item.title,
                "creators": creators,
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


def _extract_year_any(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value if 1000 <= value <= 9999 else None
    if isinstance(value, str):
        return _extract_year(value)
    if isinstance(value, dict):
        date_parts = value.get("date-parts") or value.get("dateParts")
        if (
            isinstance(date_parts, list)
            and date_parts
            and isinstance(date_parts[0], list)
            and date_parts[0]
        ):
            return _extract_year_any(date_parts[0][0])
        raw = value.get("raw") or value.get("literal")
        if isinstance(raw, str):
            return _extract_year(raw)
        return None
    if isinstance(value, list) and value:
        if isinstance(value[0], list):
            return _extract_year_any(value[0][0] if value[0] else None)
        return _extract_year_any(value[0])
    return None


def _attachment_key_from_path_field(path_field: str | None) -> str | None:
    if not path_field:
        return None
    # Common in Zotero exports: "storage:ABCD1234/foo.pdf"
    if path_field.startswith("storage:"):
        rest = path_field[len("storage:") :]
        key = rest.split("/", 1)[0].strip()
        return key or None
    # Some exports store absolute paths and include ".../storage/ABCD1234/...".
    m = _ZOTERO_STORAGE_KEY_RE.search(path_field)
    if m:
        return m.group("key").strip() or None
    return None


def _row_fields(row: dict[str, Any]) -> dict[str, Any]:
    data = row.get("data")
    return data if isinstance(data, dict) else row


def _row_key(row: dict[str, Any], fields: dict[str, Any]) -> str:
    return str(row.get("key") or row.get("itemKey") or fields.get("key") or fields.get("itemKey") or "").strip()


def load_zotero_export(path: Path) -> ZoteroExportIndex:
    # print(f"Loading {path}, exists:{path.exists()}")
    payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    rows = _as_list(payload)

    items_by_key: dict[str, ZoteroItem] = {}
    attachment_to_parent: dict[str, str] = {}

    for row in rows:
        fields = _row_fields(row)
        key = _row_key(row, fields)
        if not key:
            continue

        item_type = str(fields.get("itemType") or "").strip()
        title = fields.get("title")
        if isinstance(title, str):
            title = title.strip() or None
        else:
            title = None

        creators_raw = fields.get("creators")
        creators: list[str] = []
        if isinstance(creators_raw, list):
            for c in creators_raw:
                if isinstance(c, dict):
                    s = _creator_to_str(c)
                    if s:
                        creators.append(s)

        doi = fields.get("DOI") or fields.get("doi")
        doi = doi.strip() if isinstance(doi, str) and doi.strip() else None

        url = fields.get("url") or fields.get("URL")
        url = url.strip() if isinstance(url, str) and url.strip() else None

        citekey = fields.get("citekey") or fields.get("citationKey")
        citekey = citekey.strip() if isinstance(citekey, str) and citekey.strip() else None

        year = _extract_year_any(fields.get("date") or fields.get("issued"))

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

        parent = str(
            fields.get("parentItem")
            or fields.get("parentItemKey")
            or row.get("parentItem")
            or row.get("parentItemKey")
            or ""
        ).strip()
        if parent and (
            item_type == "attachment"
            or isinstance(fields.get("path"), str)
            or isinstance(fields.get("filename"), str)
            or isinstance(fields.get("mimeType"), str)
        ):
            attachment_to_parent[key] = parent

        attachments = fields.get("attachments")
        if isinstance(attachments, list):
            for att in attachments:
                if isinstance(att, str):
                    att_key = _attachment_key_from_path_field(att)
                    if att_key:
                        attachment_to_parent[att_key] = key
                    continue
                if not isinstance(att, dict):
                    continue
                att_key = (
                    str(att.get("key") or att.get("itemKey") or "").strip()
                    or _attachment_key_from_path_field(
                        att.get("path") if isinstance(att.get("path"), str) else None
                    )
                    or _attachment_key_from_path_field(
                        att.get("localPath") if isinstance(att.get("localPath"), str) else None
                    )
                    or _attachment_key_from_path_field(
                        att.get("file") if isinstance(att.get("file"), str) else None
                    )
                )
                if att_key:
                    attachment_to_parent[att_key] = key

        attachment_key = _attachment_key_from_path_field(
            fields.get("path") if isinstance(fields.get("path"), str) else None
        )
        if attachment_key and item_type == "attachment" and parent:
            attachment_to_parent[attachment_key] = parent

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
