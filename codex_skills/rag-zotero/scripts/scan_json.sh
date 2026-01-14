#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 /path/to/Zotero/storage [/path/to/export.json] [limit]" >&2
  exit 2
fi

STORAGE_DIR="$1"
EXPORT_JSON="${2:-}"
LIMIT="${3:-50}"

if command -v rag-zotero >/dev/null 2>&1; then
  if [[ -n "$EXPORT_JSON" ]]; then
    rag-zotero scan --json --storage-dir "$STORAGE_DIR" --export-json "$EXPORT_JSON" --limit "$LIMIT"
  else
    rag-zotero scan --json --storage-dir "$STORAGE_DIR" --limit "$LIMIT"
  fi
else
  if [[ -n "$EXPORT_JSON" ]]; then
    python3 -m rag_zotero.cli scan --json --storage-dir "$STORAGE_DIR" --export-json "$EXPORT_JSON" --limit "$LIMIT"
  else
    python3 -m rag_zotero.cli scan --json --storage-dir "$STORAGE_DIR" --limit "$LIMIT"
  fi
fi

