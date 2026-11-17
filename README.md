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
- Curator dashboard for notes and My documents
- Editable document names and General/Public/Private organization filters
- Local PDF title detection from metadata or prominent opening-page text
- Geometry-ordered PDF text extraction using `pdfplumber`, with explicit
  `pypdf` compatibility mode
- Coordinate-aware ruled-table extraction using `pdfplumber`
- Deterministic text-cleaning pipeline
- Heading-aware and page-aware document chunking
- Persistent generated notes for smaller documents
- Structural-only indexing for large documents
- Source-document and neighboring-chunk navigation
- Re-indexing and generated-output management
- JSON API endpoints for notes, documents, and structural segments

## Document Names and Organization

Open a document in **My documents**, then expand **Name and organization**
to rename it or assign a Public/Private label. General shows all documents;
the labels organize content and do not publish it or enforce access permissions.
Renaming preserves source filenames, document IDs, note IDs, and stored paths.
Generated search-note titles reflect the current name without re-ingestion.

New PDF imports try a readable title from PDF metadata or prominent text on
the first five pages, including an edition label when available. Existing
imports offer **Suggest name from PDF** for review before saving. Detection is
heuristic and editable; scanned PDFs without extractable text retain their
filename until you enter a name. No model service or OCR is required.

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

To recover a small range without ingesting the document again:

```bash
python3 extract_table_layout.py DOCUMENT_ID --pages 31-39
```

Page numbers refer to the PDF viewer's page count. Selected pages are scanned
even when an older index classified their tables as prose. Matching captions
receive table links while entry IDs and source spans remain intact. Other table
layouts are retained; overwritten table shards are backed up too.

Numeric tables with ruled columns and packed text rows can be split into cells
when every row aligns completely. Original ruled cells and their text remain in
the sidecar alongside recovered cell coordinates. Incomplete rows retain the
original extraction. Values are copied from the PDF, never filled by arithmetic.

An individual cell is available at
`/api/document/DOCUMENT_ID/table/LAYOUT_ID/cell/ROW/COLUMN`.
Rows and columns are one-based and include any header row. The response includes
the value, PDF page, and available source coordinates.

The Handbook pilot has a separate, independent arithmetic check:

```bash
python3 tools/verify_prime_table_pilot.py /path/to/Machinery-1.pdf
```

This checks PDF pages 31–39 and reports discrepancies without altering values.
It preserves the book's printed `P` for 1 as a documented source exception.

Older monolithic table-layout files can be converted without rescanning the
source PDF:

```bash
python3 shard_table_layout.py DOCUMENT_ID
```

Structural-only documents created with the older `pypdf` text order can be
re-extracted in place while retaining the same document ID and table layouts:

```bash
python3 reextract_structure.py DOCUMENT_ID
```

The command completes extraction and rebuilding before replacing anything,
then backs up the existing metadata, extracted text, cleaned text, and
structural index.

Caption-led vector drawings and embedded images can be rendered into linked
figure shards. Use `--pages` for a controlled pilot before scanning every
caption-bearing page:

```bash
python3 extract_figure_layout.py DOCUMENT_ID --pages 754
```

The command preserves the source PDF, backs up metadata and the structural
index, and stores cropped PNG figures under the document's `figure_layouts/`
directory. Omitting `--pages` scans pages whose extracted text contains a
figure caption.

Table contexts and equation contexts with suspect extraction expose an
**Original PDF verification** panel in the web UI. The panel renders source
pages lazily, caches them under the document's `source_previews/` directory,
and keeps the original page image authoritative for formulas and layout. No
rebuild or separate extraction command is required.

**View original** is available throughout PDF document browsing, structural
entry cards, generated-note pages, and search results when the archived source
exists. Entry links open the PDF at the entry's source page. Ordinary prose
contexts also include a collapsed **Original PDF pages** preview, without
needing an extraction warning. These controls never modify the source PDF.

Explicit named numeric tables (including the prime/factor tables) are also
recognized without a numbered `Table 1` caption. Older flattened chunks expose
original PDF pages immediately, with raw table text collapsed until column
geometry is recovered. A rebuild is only needed to update their stored table
classification; viewing the original pages does not require one.

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

## Reproducible verification (WO-002)

The initial tested baseline is Linux with Python 3.12. Runtime dependencies are
listed in `requirements.txt`; `requirements.lock` pins their transitive versions
without pytest. Development inputs are in `requirements-dev.in` and their complete
resolved environment is pinned in `requirements-dev.lock`. Locks are Linux/Python
3.12 version pins, not cryptographic package hashes or a cross-platform guarantee.

From a disposable checkout, run the same command used in CI:

```bash
python3.12 -m venv /tmp/archive-test-venv
/tmp/archive-test-venv/bin/python -m pip install -r requirements-dev.lock
PYTHON_BIN=/tmp/archive-test-venv/bin/python bash scripts/verify.sh /tmp/archive-test-reports
```

Use fresh paths for each clean install. Runtime-only installation uses
`python -m pip install -r requirements.lock`. The wrapper checks dependencies and
runs all existing tests with JUnit output, copying tracked source (including
pending tracked edits) into a temporary directory. Stage new verification files
before using it. Untracked notes, PDFs and local data are excluded. Tests create
synthetic fixtures under temporary paths; no personal corpus is required. Reports
contain dependency versions, pip diagnostics and test/JUnit results; CI also retains
installation diagnostics. GitHub keeps these synthetic-only artifacts for 14 days,
on success and failure. Uploading evidence cannot override a failed test step.

To refresh locks intentionally, create a fresh Python 3.12 venv, install from
`requirements-dev.in`, run `python -m pip freeze > requirements-dev.lock`, and
resolve the runtime-only inputs in another fresh venv with
`python -m pip install -r requirements.txt` followed by
`python -m pip freeze > requirements.lock`. Review every version change. Run the
verification recipe, then repeat a clean install from the new development lock
and compare `pip freeze` output. Do not refresh dependencies as unrelated cleanup.
The pip/venv bootstrap itself is supplied by the Python installation.

A green baseline covers the existing tests, not all application safety or real-PDF
fidelity. Known WO-003/004 defects remain outside this infrastructure change.
Contributor scope, correction bounds and handoff requirements are in `AGENTS.md`.
