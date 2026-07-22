from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime

from ingestion.registry import create_document_record, write_metadata
from ingestion.extractors import extract_text_from_pdf, save_extracted_text
from ingestion.cleaners import clean_extracted_text, save_cleaned_text
from ingestion.chunkers import build_chunks, save_chunks
from ingestion.indexer import (
    index_chunks_to_generated_notes,
    index_structural_doc_to_generated_note,
)
from ingestion.structural_index import build_structural_index, save_structural_index

def determine_chunk_storage_mode(
    chunk_count: int,
    storage_mode: str = "auto",
    persistent_chunk_limit: int = 300,
) -> str:
    """
    Decide whether this document should store chunks persistently
    or remain structural-only.

    Modes:
    - auto: choose based on chunk count
    - persistent: always persist chunks + generated notes
    - structural_only: skip persistent generated chunk storage
    """
    valid_modes = {"auto", "persistent", "structural_only"}
    if storage_mode not in valid_modes:
        raise ValueError(
            f"Invalid storage_mode '{storage_mode}'. "
            f"Expected one of: {', '.join(sorted(valid_modes))}"
        )

    if storage_mode == "persistent":
        return "persistent"

    if storage_mode == "structural_only":
        return "structural_only"

    if chunk_count <= persistent_chunk_limit:
        return "persistent"

    return "structural_only"

def ingest_document(
    source_file: str,
    category_path: str,
    max_chars: int = 1200,
    storage_mode: str = "auto",
    persistent_chunk_limit: int = 300,
) -> dict:
    """
    Run the full ingestion pipeline for a single document.

    Steps:
    1. Register document
    2. Extract raw text
    3. Save extracted text
    4. Clean text
    5. Save cleaned text
    6. Build chunks in memory
    7. Determine chunk storage mode
    8. Save structural index
    9. Persist chunks only for persistent-mode documents
    10. Update metadata
    11. Generate searchable notes:
        - chunk notes for persistent documents
        - one document note for structural-only documents
    """
    metadata = create_document_record(source_file, category_path)

    doc_id = metadata["doc_id"]
    doc_root = Path(metadata["doc_root"])
    stored_source_path = doc_root / metadata["stored_source_filename"]
    extracted_text_path = Path(metadata["extracted_text_file"])
    cleaned_text_path = doc_root / "cleaned_text.txt"
    chunks_path = Path(metadata["chunks_file"])
    structural_index_path = doc_root / "structural_index.json"

    # Step 2: extract
    extraction_result = extract_text_from_pdf(stored_source_path)
    save_extracted_text(extracted_text_path, extraction_result["text"])

    # Step 3: clean
    cleaned_text = clean_extracted_text(extraction_result["text"])
    save_cleaned_text(cleaned_text_path, cleaned_text)

    # Step 4: chunk
    chunks = build_chunks(doc_id, cleaned_text, max_chars=max_chars)

    resolved_storage_mode = determine_chunk_storage_mode(
        chunk_count=len(chunks),
        storage_mode=storage_mode,
        persistent_chunk_limit=persistent_chunk_limit,
    )

    # Step 4.5: build structural index
    structural_index = build_structural_index(chunks)
    save_structural_index(structural_index_path, structural_index)

    if resolved_storage_mode == "persistent":
        save_chunks(chunks_path, chunks)

    # Step 5: update metadata
    metadata["status"] = "chunked"
    metadata["extractor"] = extraction_result["extractor"]
    metadata["page_count"] = extraction_result["page_count"]
    metadata["cleaned_text_file"] = str(cleaned_text_path)
    metadata["chunk_count"] = len(chunks)

    metadata["chunk_storage_mode"] = resolved_storage_mode
    metadata["chunk_count_estimate"] = len(chunks)
    metadata["structural_index_file"] = str(structural_index_path)
    metadata["structural_index_entry_count"] = len(structural_index)
    metadata["promoted_chunk_count"] = 0
    metadata["chunks_file"] = str(chunks_path) if resolved_storage_mode == "persistent" else None

    metadata["updated_at"] = datetime.now().isoformat(timespec="seconds")

    write_metadata(metadata["metadata_file"], metadata)

    if resolved_storage_mode == "persistent":
        index_result = index_chunks_to_generated_notes(metadata["metadata_file"])
        metadata["generated_note_count"] = index_result["note_count"]
    else:
        index_result = index_structural_doc_to_generated_note(metadata["metadata_file"])
        metadata["generated_note_count"] = index_result["note_count"]

    write_metadata(metadata["metadata_file"], metadata)
    return metadata


def print_summary(metadata: dict) -> None:
    """
    Print a clean ingestion summary.
    """
    print("\nIngestion successful.\n")
    print(f"doc_id: {metadata['doc_id']}")
    print(f"title: {metadata['title']}")
    print(f"source_filename: {metadata['source_filename']}")
    print(f"category_path: {metadata['category_path']}")
    print(f"file_type: {metadata['file_type']}")
    print(f"status: {metadata['status']}")
    print(f"page_count: {metadata.get('page_count')}")
    print(f"chunk_count: {metadata.get('chunk_count')}")
    print(f"chunk_storage_mode: {metadata.get('chunk_storage_mode')}")
    print(f"chunk_count_estimate: {metadata.get('chunk_count_estimate')}")
    print(f"structural_index_file: {metadata.get('structural_index_file')}")
    print(f"structural_index_entry_count: {metadata.get('structural_index_entry_count')}")
    print(f"promoted_chunk_count: {metadata.get('promoted_chunk_count')}")
    print(f"generated_note_count: {metadata.get('generated_note_count')}")
    print(f"doc_root: {metadata['doc_root']}")
    print(f"metadata_file: {metadata['metadata_file']}")
    print(f"extracted_text_file: {metadata['extracted_text_file']}")
    print(f"cleaned_text_file: {metadata.get('cleaned_text_file')}")
    print(f"chunks_file: {metadata['chunks_file']}")

def main() -> None:
    if len(sys.argv) < 3:
        print("Usage:")
        print('  python3 ingest.py "/path/to/file.pdf" "category/path"')
        sys.exit(1)

    source_file = sys.argv[1]
    category_path = sys.argv[2]

    try:
        metadata = ingest_document(source_file, category_path)
        print_summary(metadata)
    except Exception as e:
        print(f"\nIngestion failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
