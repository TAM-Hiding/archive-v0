from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from ingestion.registry import DOCUMENTS_ROOT, write_metadata
from ingestion.table_layout import write_sharded_table_layout_store


def shard_document_table_layout(
    doc_id: str,
    documents_root: str | Path = DOCUMENTS_ROOT,
) -> dict[str, Any]:
    """Convert an existing monolithic table-layout sidecar without rescanning."""
    if not doc_id or Path(doc_id).name != doc_id:
        raise ValueError("doc_id must be one plain directory name")

    doc_root = Path(documents_root) / doc_id
    metadata_path = doc_root / "metadata.json"
    if not metadata_path.is_file():
        raise FileNotFoundError(f"Document metadata not found: {metadata_path}")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    layout_path = Path(metadata.get("table_layout_file", ""))
    if not layout_path.is_file():
        raise FileNotFoundError(f"Table layout file not found: {layout_path}")

    payload = json.loads(layout_path.read_text(encoding="utf-8"))
    if payload.get("storage_mode") == "sharded":
        return {
            "doc_id": doc_id,
            "already_sharded": True,
            "layout_count": payload.get("layout_count", 0),
            "table_layout_file": str(layout_path),
            "table_layout_backup": None,
        }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    layout_backup = doc_root / f"table_layout.backup-{timestamp}.json"
    metadata_backup = doc_root / f"metadata.backup-{timestamp}.json"
    shutil.copy2(layout_path, layout_backup)
    shutil.copy2(metadata_path, metadata_backup)

    manifest = write_sharded_table_layout_store(layout_path, payload)
    sharded_at = datetime.now().isoformat(timespec="seconds")
    metadata.update({
        "table_layout_storage_mode": "sharded",
        "table_layout_sharded_at": sharded_at,
        "updated_at": sharded_at,
    })
    write_metadata(metadata_path, metadata)

    return {
        "doc_id": doc_id,
        "already_sharded": False,
        "layout_count": manifest["layout_count"],
        "table_layout_file": str(layout_path),
        "table_layout_backup": str(layout_backup),
        "metadata_backup": str(metadata_backup),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Split an existing table_layout.json into a compact manifest and "
            "one file per table without rescanning the source PDF."
        )
    )
    parser.add_argument("doc_id", help="Existing Archive document ID")
    args = parser.parse_args()

    result = shard_document_table_layout(args.doc_id)
    print("\nTable layout sharding successful.\n")
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
