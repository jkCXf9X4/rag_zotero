---
name: rag-zotero
description: Use when you need to search a local Zotero storage folder using this repo's rag-zotero CLI (scan/index/query) and return results (prefer --json for agent-readable output).
---

# rag-zotero (Codex CLI skill)

## What this skill is for

Use this when the user asks to:
- search their indexed Zotero PDFs
- enrich results with Zotero/BetterBibTeX JSON export metadata

## Commands (agent-friendly)

Prefer machine-readable output flags:
- `rag-zotero query --json "..." --n 10`

If `rag-zotero` is not on `PATH`, run via module:
- `python3 -m rag_zotero.cli scan ...`
- `python3 -m rag_zotero.cli query ...`

## Typical workflows

### Search (RAG query)
1) Run:
   - `rag-zotero query --json "YOUR QUESTION" --n 5`
2) Use returned `results[*].snippet` and `results[*].metadata` to answer, citing `source_path` and `page`.

### Diagnose missing metadata matches
- Run `rag-zotero scan --storage-dir ... --export-json ...  --json` (human output includes a warning if no matches).
- If matches are zero, request a different export format: Zotero JSON or BetterBibTeX JSON (not CSL/bibliography JSON).

