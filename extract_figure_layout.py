from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from ingestion.figure_layout import (
    extract_pdf_figure_layouts,
    find_figure_candidate_pages,
    parse_page_spec,
    write_figure_manifest,
)
from ingestion.figure_links import link_figure_layouts_to_entries
from ingestion.registry import DOCUMENTS_ROOT, write_metadata


def extract_document_figure_layout(
    doc_id: str,
    documents_root: str | Path = DOCUMENTS_ROOT,
    page_numbers: set[int] | None = None,
) -> dict[str, Any]:
    """Render caption-led PDF figures and link them to structural entries."""
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
    cleaned_text_path = Path(metadata.get("cleaned_text_file", ""))
    if not cleaned_text_path.is_file():
        raise FileNotFoundError(f"Cleaned text not found: {cleaned_text_path}")

    cleaned_text = cleaned_text_path.read_text(encoding="utf-8")
    selected_pages = (
        set(page_numbers)
        if page_numbers is not None
        else find_figure_candidate_pages(cleaned_text)
    )
    if not selected_pages:
        raise ValueError("No caption-bearing figure candidate pages found")

    temporary_image_directory = doc_root / "figure_layouts.extract.tmp"
    if temporary_image_directory.exists():
        shutil.rmtree(temporary_image_directory)
    layouts = extract_pdf_figure_layouts(
        source_path,
        temporary_image_directory,
        selected_pages,
    )
    if not layouts:
        shutil.rmtree(temporary_image_directory)
        raise ValueError("No caption-led figure geometry found on selected pages")

    entries = json.loads(structural_index_path.read_text(encoding="utf-8"))
    linked_figure_count = link_figure_layouts_to_entries(
        entries,
        layouts,
        cleaned_text,
    )

    temporary_manifest_path = doc_root / "figure_layout.extract.tmp.json"
    write_figure_manifest(
        temporary_manifest_path,
        doc_id,
        metadata.get("source_filename", ""),
        layouts,
    )
    temporary_index_path = doc_root / "structural_index.figure-layout.tmp.json"
    temporary_index_path.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    metadata_backup = doc_root / f"metadata.backup-{timestamp}.json"
    structural_backup = doc_root / f"structural_index.backup-{timestamp}.json"
    manifest_path = doc_root / "figure_layout.json"
    image_directory = doc_root / "figure_layouts"
    manifest_backup: Path | None = None
    image_directory_backup: Path | None = None
    shutil.copy2(metadata_path, metadata_backup)
    shutil.copy2(structural_index_path, structural_backup)
    if manifest_path.is_file():
        manifest_backup = doc_root / f"figure_layout.backup-{timestamp}.json"
        shutil.copy2(manifest_path, manifest_backup)
    if image_directory.is_dir():
        image_directory_backup = (
            doc_root / f"figure_layouts.backup-{timestamp}"
        )
        image_directory.replace(image_directory_backup)

    temporary_image_directory.replace(image_directory)
    temporary_manifest_path.replace(manifest_path)
    temporary_index_path.replace(structural_index_path)

    extracted_at = datetime.now().isoformat(timespec="seconds")
    metadata.update({
        "figure_layout_file": str(manifest_path),
        "figure_layout_storage_mode": "image_shards",
        "figure_layout_count": len(layouts),
        "figure_layout_linked_count": linked_figure_count,
        "figure_layout_extracted_at": extracted_at,
        "updated_at": extracted_at,
    })
    write_metadata(metadata_path, metadata)

    total_image_bytes = sum(
        path.stat().st_size for path in image_directory.glob("*.png")
    )
    return {
        "doc_id": doc_id,
        "candidate_page_count": len(selected_pages),
        "figure_layout_count": len(layouts),
        "linked_figure_count": linked_figure_count,
        "figure_image_bytes": total_image_bytes,
        "figure_layout_file": str(manifest_path),
        "metadata_backup": str(metadata_backup),
        "structural_index_backup": str(structural_backup),
        "figure_layout_backup": (
            str(manifest_backup) if manifest_backup else None
        ),
        "figure_image_directory_backup": (
            str(image_directory_backup) if image_directory_backup else None
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract caption-led vector and raster PDF figures."
    )
    parser.add_argument("doc_id", help="Existing Archive document ID")
    parser.add_argument(
        "--pages",
        help="Optional one-based page list/ranges, for example 754,760-762",
    )
    args = parser.parse_args()
    pages = parse_page_spec(args.pages) if args.pages else None
    result = extract_document_figure_layout(args.doc_id, page_numbers=pages)
    print("\nFigure layout extraction successful.\n")
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
