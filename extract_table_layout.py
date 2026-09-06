from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from ingestion.registry import DOCUMENTS_ROOT, write_metadata
from ingestion.table_layout import (
    extract_pdf_table_layouts,
    match_layout_to_caption,
    write_sharded_table_layout_store,
)


def extract_document_table_layout(
    doc_id: str,
    documents_root: str | Path = DOCUMENTS_ROOT,
) -> dict[str, Any]:
    """Build a PDF-coordinate sidecar and link it to structural table entries."""
    if not doc_id or Path(doc_id).name != doc_id:
        raise ValueError("doc_id must be one plain directory name")

    doc_root = Path(documents_root) / doc_id
    metadata_path = doc_root / "metadata.json"
    if not metadata_path.is_file():
        raise FileNotFoundError(f"Document metadata not found: {metadata_path}")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    source_path = doc_root / metadata.get("stored_source_filename", "")
    if not source_path.is_file():
        raise FileNotFoundError(f"Stored source PDF not found: {source_path}")

    structural_index_path = Path(metadata.get("structural_index_file", ""))
    if not structural_index_path.is_file():
        raise FileNotFoundError(
            f"Structural index not found: {structural_index_path}"
        )

    entries = json.loads(structural_index_path.read_text(encoding="utf-8"))
    table_entries = [
        entry for entry in entries if entry.get("content_type") == "table"
    ]
    page_numbers = {
        int(entry["page_start"])
        for entry in table_entries
        if entry.get("page_start") is not None
    }

    layouts = extract_pdf_table_layouts(source_path, page_numbers=page_numbers)
    layouts_by_id = {layout["layout_id"]: layout for layout in layouts}
    linked_entry_count = 0

    for entry in table_entries:
        page_number = entry.get("page_start")
        if page_number is None:
            continue
        layout = match_layout_to_caption(
            layouts,
            int(page_number),
            entry.get("table_caption", ""),
        )
        if layout is None:
            continue

        entry["table_layout_id"] = layout["layout_id"]
        layout_text = layout.get("reading_order_text", "").strip()
        source_search_text = entry.get("search_text", "").strip()
        if layout_text and layout_text not in source_search_text:
            entry["search_text"] = "\n\n".join(
                value for value in (source_search_text, layout_text) if value
            )
        linked_entry_count += 1

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    metadata_backup = doc_root / f"metadata.backup-{timestamp}.json"
    structural_backup = (
        doc_root / f"structural_index.backup-{timestamp}.json"
    )
    layout_path = doc_root / "table_layout.json"
    layout_backup: Path | None = None

    shutil.copy2(metadata_path, metadata_backup)
    shutil.copy2(structural_index_path, structural_backup)
    if layout_path.is_file():
        layout_backup = doc_root / f"table_layout.backup-{timestamp}.json"
        shutil.copy2(layout_path, layout_backup)

    layout_payload = {
        "doc_id": doc_id,
        "source_filename": metadata.get("source_filename", ""),
        "layout_count": len(layouts),
        "layouts": layouts,
    }
    temporary_index_path = doc_root / "structural_index.table-layout.tmp.json"
    write_sharded_table_layout_store(layout_path, layout_payload)
    temporary_index_path.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary_index_path.replace(structural_index_path)

    extracted_at = datetime.now().isoformat(timespec="seconds")
    metadata.update({
        "table_layout_file": str(layout_path),
        "table_layout_storage_mode": "sharded",
        "table_layout_count": len(layouts),
        "table_layout_linked_entry_count": linked_entry_count,
        "table_layout_extracted_at": extracted_at,
        "updated_at": extracted_at,
    })
    write_metadata(metadata_path, metadata)

    return {
        "doc_id": doc_id,
        "table_page_count": len(page_numbers),
        "table_layout_count": len(layouts),
        "linked_entry_count": linked_entry_count,
        "table_layout_file": str(layout_path),
        "metadata_backup": str(metadata_backup),
        "structural_index_backup": str(structural_backup),
        "table_layout_backup": str(layout_backup) if layout_backup else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Extract coordinate-aware PDF table layouts for one ingested document "
            "and link them to its structural table entries."
        )
    )
    parser.add_argument("doc_id", help="Existing Archive document ID")
    args = parser.parse_args()

    result = extract_document_table_layout(args.doc_id)
    print("\nTable layout extraction successful.\n")
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
