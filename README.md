# rag_zotero

Index academic PDFs (typically stored in Zotero’s local `storage/`) into a local vector DB and query them using embeddings.

This repo intentionally starts minimal:
- **Source**: local Zotero storage folder (PDFs / text files).
- **Index**: local persistent Chroma DB in `./data/chroma/`.
- **Embeddings**: OpenAI by default; optional local embeddings via `sentence-transformers`.

## Quickstart

### 1) Create a venv + install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

### 2) Configure

Copy `.env.example` to `.env` and set at least:
- `OPENAI_API_KEY` (recommended), or install local embeddings extra.

### 3) Index your Zotero PDFs

Point at your Zotero `storage/` directory (example paths):
- Linux: `~/Zotero/storage`
- macOS: `~/Zotero/storage`
- Windows: `%USERPROFILE%\\Zotero\\storage`

```bash
rag-zotero index --storage-dir "$HOME/Zotero/storage"
```

### 4) Query

```bash
rag-zotero query "What is temporal independence in co-simulation?"
```

## Commands

- `rag-zotero doctor`: show config, verify dependencies (use `--live` to do an actual embedding call).
- `rag-zotero scan --storage-dir ...`: list candidate files.
- `rag-zotero index --storage-dir ...`: extract + chunk + embed + store.
- `rag-zotero query "...":` semantic search against the index.

## Notes / limitations

- This scans *files* in Zotero `storage/` and doesn’t (yet) resolve Zotero item metadata (titles, authors, collections).
- PDFs that are image-only (no text layer) will extract poorly; OCR can be added later.
