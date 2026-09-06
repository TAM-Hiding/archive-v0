from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from ingestion.chunkers import build_chunks
from ingestion.indexer import index_structural_doc_to_generated_note
from ingestion.registry import DOCUMENTS_ROOT, write_metadata
from ingestion.structural_index import build_structural_index, save_structural_index


def rebuild_structural_document(
    doc_id: str,
    documents_root: str | Path = DOCUMENTS_ROOT,
) -> dict[str, Any]:
    """Rebuild one structural-only document from its cleaned text in place."""
    if not doc_id or Path(doc_id).name != doc_id:
        raise ValueError("doc_id must be one plain directory name")

    doc_root = Path(documents_root) / doc_id
    metadata_path = doc_root / "metadata.json"

    if not metadata_path.is_file():
        raise FileNotFoundError(f"Document metadata not found: {metadata_path}")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    if metadata.get("chunk_storage_mode") != "structural_only":
        raise ValueError(
            "In-place structure rebuild currently supports only "
            "structural-only documents"
        )

    cleaned_text_path = Path(metadata.get("cleaned_text_file", ""))
    if not cleaned_text_path.is_file():
        raise FileNotFoundError(
            f"Cleaned text not found: {cleaned_text_path}"
        )

    cleaned_text = cleaned_text_path.read_text(encoding="utf-8")
    chunks = build_chunks(doc_id, cleaned_text)
    structural_index = build_structural_index(chunks)

    structural_index_path = doc_root / "structural_index.json"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    metadata_backup = doc_root / f"metadata.backup-{timestamp}.json"
    structural_backup: Path | None = None

    shutil.copy2(metadata_path, metadata_backup)

    if structural_index_path.is_file():
        structural_backup = (
            doc_root / f"structural_index.backup-{timestamp}.json"
        )
        shutil.copy2(structural_index_path, structural_backup)

    temporary_index_path = doc_root / "structural_index.rebuild.tmp.json"
    save_structural_index(temporary_index_path, structural_index)
    temporary_index_path.replace(structural_index_path)

    rebuilt_at = datetime.now().isoformat(timespec="seconds")
    metadata.update({
        "chunk_count": len(chunks),
        "chunk_count_estimate": len(chunks),
        "structural_index_file": str(structural_index_path),
        "structural_index_entry_count": len(structural_index),
        "structure_rebuilt_at": rebuilt_at,
        "updated_at": rebuilt_at,
    })
    write_metadata(metadata_path, metadata)

    index_result = index_structural_doc_to_generated_note(metadata_path)

    return {
        "doc_id": doc_id,
        "chunk_count": len(chunks),
        "structural_index_file": str(structural_index_path),
        "metadata_backup": str(metadata_backup),
        "structural_index_backup": (
            str(structural_backup) if structural_backup else None
        ),
        "generated_note_count": index_result["note_count"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild a structural-only document from its existing "
            "cleaned_text.txt without creating a new document ID."
        )
    )
    parser.add_argument("doc_id", help="Existing Archive document ID")
    args = parser.parse_args()

    result = rebuild_structural_document(args.doc_id)

    print("\nStructural rebuild successful.\n")
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
