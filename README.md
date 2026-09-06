# Archive v0

Archive v0 is a local-first personal knowledge archive for storing, searching, curating, and navigating notes and reference documents.

It combines a Flask web interface with a deterministic PDF ingestion pipeline. Documents can be extracted, cleaned, divided into searchable chunks, structurally indexed, and connected back to their original source material.

> Archive v0 is under active development. The current repository contains the application code, not actual content.

## Current Features

- Local Markdown note storage
- Full-text note search
- Weighted search across titles, tags, aliases, paths, and body text
- Conservative fuzzy term expansion
- Note creation and editing
- Folder/category navigation
- Curator dashboard for notes and ingested documents
- PDF text extraction using `pypdf`
- Coordinate-aware ruled-table extraction using `pdfplumber`
- Deterministic text-cleaning pipeline
- Heading-aware and page-aware document chunking
- Persistent generated notes for smaller documents
- Structural-only indexing for large documents
- Source-document and neighboring-chunk navigation
- Re-indexing and generated-output management
- JSON API endpoints for notes, documents, and structural segments

## Table Layout Extraction

After ingesting or structurally rebuilding a PDF, extract its ruled-table
geometry with:

```bash
python3 extract_table_layout.py DOCUMENT_ID
```

The command reads the Archive's stored source PDF, inspects only pages already
classified as containing tables. It writes a compact `table_layout.json`
manifest plus one JSON file per table under `table_layouts/`. The table shards
preserve detected cells, merged grid positions, and positioned text lines; the
manifest links matching structural entries by caption and page. The command
also adds coordinate-derived reading order to table search text. Existing
metadata and structural-index files are backed up before replacement.

Older monolithic table-layout files can be converted without rescanning the
source PDF:

```bash
python3 shard_table_layout.py DOCUMENT_ID
```

## Project Structure

```text
archive-v0/
├── app.py                 # Flask web application and routes
├── archive.py             # Search, note management, and archive operations
├── ingest.py              # Document ingestion entry point
├── ingestion/             # Extraction, cleaning, chunking, indexing, and registry
├── templates/             # Flask/Jinja HTML templates
├── tools/                 # Maintenance and backfill utilities
├── test_*.py              # Current automated tests
├── requirements.txt       # Python dependencies
├── CHANGELOG.md           # Project history
└── TODO.md                # Planned work
