from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from ingestion.chunkers import build_chunks
from ingestion.cleaners import clean_extracted_text, save_cleaned_text
from ingestion.extractors import extract_text_from_pdf, save_extracted_text
from ingestion.indexer import index_structural_doc_to_generated_note
from ingestion.registry import DOCUMENTS_ROOT, write_metadata
from ingestion.structural_index import build_structural_index, save_structural_index
from ingestion.table_links import restore_table_layout_links


def reextract_structural_document(
    doc_id: str,
    documents_root: str | Path = DOCUMENTS_ROOT,
    extractor: str = "pdfplumber",
) -> dict[str, Any]:
    """Re-extract and rebuild one structural-only document in place."""
    if not doc_id or Path(doc_id).name != doc_id:
        raise ValueError("doc_id must be one plain directory name")

    doc_root = Path(documents_root) / doc_id
    metadata_path = doc_root / "metadata.json"
    if not metadata_path.is_file():
        raise FileNotFoundError(f"Document metadata not found: {metadata_path}")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("chunk_storage_mode") != "structural_only":
        raise ValueError(
            "In-place re-extraction currently supports only structural-only "
            "documents"
        )

    source_path = doc_root / metadata.get("stored_source_filename", "")
    if not source_path.is_file():
        raise FileNotFoundError(f"Stored source PDF not found: {source_path}")

    extracted_text_path = Path(metadata.get("extracted_text_file", ""))
    cleaned_text_path = Path(metadata.get("cleaned_text_file", ""))
    structural_index_path = Path(metadata.get("structural_index_file", ""))
    for label, path in (
        ("extracted text", extracted_text_path),
        ("cleaned text", cleaned_text_path),
        ("structural index", structural_index_path),
    ):
        if not path.is_file():
            raise FileNotFoundError(f"Existing {label} not found: {path}")

    extraction_result = extract_text_from_pdf(source_path, extractor=extractor)
    cleaned_text = clean_extracted_text(extraction_result["text"])
    chunks = build_chunks(doc_id, cleaned_text)
    structural_index = build_structural_index(chunks)
    linked_table_entry_count = restore_table_layout_links(
        structural_index,
        metadata,
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    metadata_backup = doc_root / f"metadata.backup-{timestamp}.json"
    extracted_backup = doc_root / f"extracted_text.backup-{timestamp}.txt"
    cleaned_backup = doc_root / f"cleaned_text.backup-{timestamp}.txt"
    structural_backup = doc_root / f"structural_index.backup-{timestamp}.json"
    shutil.copy2(metadata_path, metadata_backup)
    shutil.copy2(extracted_text_path, extracted_backup)
    shutil.copy2(cleaned_text_path, cleaned_backup)
    shutil.copy2(structural_index_path, structural_backup)

    temporary_extracted_path = doc_root / "extracted_text.reextract.tmp.txt"
    temporary_cleaned_path = doc_root / "cleaned_text.reextract.tmp.txt"
    temporary_index_path = doc_root / "structural_index.reextract.tmp.json"
    save_extracted_text(temporary_extracted_path, extraction_result["text"])
    save_cleaned_text(temporary_cleaned_path, cleaned_text)
    save_structural_index(temporary_index_path, structural_index)
    temporary_extracted_path.replace(extracted_text_path)
    temporary_cleaned_path.replace(cleaned_text_path)
    temporary_index_path.replace(structural_index_path)

    reextracted_at = datetime.now().isoformat(timespec="seconds")
    metadata.update({
        "extractor": extraction_result["extractor"],
        "page_count": extraction_result["page_count"],
        "chunk_count": len(chunks),
        "chunk_count_estimate": len(chunks),
        "structural_index_entry_count": len(structural_index),
        "table_layout_linked_entry_count": linked_table_entry_count,
        "text_reextracted_at": reextracted_at,
        "structure_rebuilt_at": reextracted_at,
        "updated_at": reextracted_at,
    })
    write_metadata(metadata_path, metadata)
    index_result = index_structural_doc_to_generated_note(metadata_path)

    return {
        "doc_id": doc_id,
        "extractor": extraction_result["extractor"],
        "page_count": extraction_result["page_count"],
        "chunk_count": len(chunks),
        "table_layout_linked_entry_count": linked_table_entry_count,
        "metadata_backup": str(metadata_backup),
        "extracted_text_backup": str(extracted_backup),
        "cleaned_text_backup": str(cleaned_backup),
        "structural_index_backup": str(structural_backup),
        "generated_note_count": index_result["note_count"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Re-extract a structural-only document from its stored PDF using "
            "geometry-aware text order, preserving its document ID."
        )
    )
    parser.add_argument("doc_id", help="Existing Archive document ID")
    parser.add_argument(
        "--extractor",
        choices=("pdfplumber", "pypdf"),
        default="pdfplumber",
    )
    args = parser.parse_args()

    result = reextract_structural_document(
        args.doc_id,
        extractor=args.extractor,
    )
    print("\nStructural re-extraction successful.\n")
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
