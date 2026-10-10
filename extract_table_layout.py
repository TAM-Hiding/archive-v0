from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from ingestion.registry import DOCUMENTS_ROOT, write_metadata
from ingestion.table_captions import named_table_caption
from ingestion.table_layout import (
    extract_pdf_table_layouts,
    match_layout_to_caption,
    write_sharded_table_layout_store,
)


def extract_document_table_layout(
    doc_id: str,
    documents_root: str | Path = DOCUMENTS_ROOT,
    page_numbers: list[int] | None = None,
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
    selected_pages = set(page_numbers) if page_numbers is not None else None
    if selected_pages is not None and (not selected_pages or min(selected_pages) < 1):
        raise ValueError("Select at least one positive PDF page number")
    captions = {index: (entry.get("table_caption")
                       or named_table_caption(entry.get("preview", ""))
                       or named_table_caption(entry.get("search_text", "")))
                for index, entry in enumerate(entries)}
    table_entries = [entry for index, entry in enumerate(entries)
                     if (entry.get("content_type") == "table" or captions[index])
                     and (selected_pages is None or entry.get("page_start") in selected_pages)]
    extraction_pages = selected_pages if selected_pages is not None else {
        int(entry["page_start"])
        for entry in table_entries
        if entry.get("page_start") is not None
    }

    layouts = extract_pdf_table_layouts(source_path, page_numbers=extraction_pages)
    linked_entry_count = 0

    for entry in table_entries:
        page_number = entry.get("page_start")
        if page_number is None:
            continue
        layout = match_layout_to_caption(
            layouts,
            int(page_number),
            entry.get("table_caption") or named_table_caption(entry.get("preview", ""))
            or named_table_caption(entry.get("search_text", "")) or "",
        )
        if layout is None:
            continue

        entry["table_layout_id"] = layout["layout_id"]
        if entry.get("content_type") != "table":
            entry["content_type"] = "table"
            entry["table_caption"] = layout.get("caption", "")
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

    # A targeted pilot must retain every unrelated recovered table. Preserve
    # compact records directly for sharded stores; migrate old inline records.
    preserved_records = []
    if selected_pages is not None and layout_path.is_file():
        old_manifest = json.loads(layout_path.read_text(encoding="utf-8"))
        old_records = [record for record in old_manifest.get("layouts", [])
                       if record.get("page_number") not in selected_pages]
        if old_manifest.get("storage_mode") == "sharded":
            preserved_records = old_records
        else:
            layouts = old_records + layouts

    shard_backup_directory = doc_root / f"table_layouts.backup-{timestamp}"
    for layout in layouts:
        old_shard = doc_root / "table_layouts" / f"{layout['layout_id']}.json"
        if old_shard.is_file():
            shard_backup_directory.mkdir(exist_ok=True)
            shutil.copy2(old_shard, shard_backup_directory / old_shard.name)

    layout_payload = {
        "doc_id": doc_id,
        "source_filename": metadata.get("source_filename", ""),
        "layout_count": len(layouts),
        "layouts": layouts,
    }
    temporary_index_path = doc_root / "structural_index.table-layout.tmp.json"
    manifest = write_sharded_table_layout_store(layout_path, layout_payload,
                                                preserved_records=preserved_records)
    temporary_index_path.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary_index_path.replace(structural_index_path)

    extracted_at = datetime.now().isoformat(timespec="seconds")
    metadata.update({
        "table_layout_file": str(layout_path),
        "table_layout_storage_mode": "sharded",
        "table_layout_count": manifest["layout_count"],
        "table_layout_linked_entry_count": sum(bool(entry.get("table_layout_id"))
                                                for entry in entries),
        "table_layout_extracted_at": extracted_at,
        "updated_at": extracted_at,
    })
    write_metadata(metadata_path, metadata)

    return {
        "doc_id": doc_id,
        "table_page_count": len(extraction_pages),
        "table_layout_count": manifest["layout_count"],
        "linked_entry_count": linked_entry_count,
        "table_layout_file": str(layout_path),
        "metadata_backup": str(metadata_backup),
        "structural_index_backup": str(structural_backup),
        "table_layout_backup": str(layout_backup) if layout_backup else None,
        "table_shard_backup_directory": (str(shard_backup_directory)
                                          if shard_backup_directory.is_dir() else None),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Extract coordinate-aware PDF table layouts for one ingested document "
            "and link them to its structural table entries."
        )
    )
    parser.add_argument("doc_id", help="Existing Archive document ID")
    parser.add_argument("--pages", help="PDF pages to recover, e.g. 31-39 or 31,33,39")
    args = parser.parse_args()

    page_numbers = None
    if args.pages:
        try:
            page_numbers = []
            for part in args.pages.split(","):
                bounds = [int(value) for value in part.strip().split("-")]
                if len(bounds) == 1:
                    page_numbers.append(bounds[0])
                elif len(bounds) == 2 and bounds[1] >= bounds[0]:
                    page_numbers.extend(range(bounds[0], bounds[1] + 1))
                else:
                    raise ValueError
        except ValueError:
            parser.error("Use positive page numbers or ascending ranges, e.g. 31-39")
    result = extract_document_table_layout(args.doc_id, page_numbers=page_numbers)
    print("\nTable layout extraction successful.\n")
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
