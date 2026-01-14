#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 \"query text\" [n_results]" >&2
  exit 2
fi

QUERY="$1"
N="${2:-5}"

if command -v rag-zotero >/dev/null 2>&1; then
  rag-zotero query --json "$QUERY" --n "$N"
else
  python3 -m rag_zotero.cli query --json "$QUERY" --n "$N"
fi

