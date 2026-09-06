import json

from shard_table_layout import shard_document_table_layout


def test_shard_document_table_layout_migrates_existing_sidecar(tmp_path):
    doc_root = tmp_path / "doc_001"
    doc_root.mkdir()
    layout_path = doc_root / "table_layout.json"
    layout_path.write_text(
        json.dumps({
            "doc_id": "doc_001",
            "source_filename": "handbook.pdf",
            "layout_count": 1,
            "layouts": [{
                "layout_id": "page_0008_table_01",
                "page_number": 8,
                "table_index": 1,
                "caption": "Table 1. Preferred Fits",
                "grid": [["Fit", "Description"]],
                "cells": [],
                "reading_order_text": "Fit Description",
            }],
        }),
        encoding="utf-8",
    )
    metadata_path = doc_root / "metadata.json"
    metadata_path.write_text(
        json.dumps({
            "doc_id": "doc_001",
            "table_layout_file": str(layout_path),
        }),
        encoding="utf-8",
    )

    result = shard_document_table_layout("doc_001", tmp_path)

    assert result["already_sharded"] is False
    assert result["layout_count"] == 1
    manifest = json.loads(layout_path.read_text(encoding="utf-8"))
    assert manifest["storage_mode"] == "sharded"
    shard_path = doc_root / manifest["layouts"][0]["file"]
    assert json.loads(shard_path.read_text(encoding="utf-8"))["grid"] == [
        ["Fit", "Description"]
    ]
    assert list(doc_root.glob("table_layout.backup-*.json"))
    assert list(doc_root.glob("metadata.backup-*.json"))


def test_shard_document_table_layout_is_idempotent(tmp_path):
    doc_root = tmp_path / "doc_001"
    doc_root.mkdir()
    layout_path = doc_root / "table_layout.json"
    layout_path.write_text(
        json.dumps({
            "storage_mode": "sharded",
            "layout_count": 3,
            "layouts": [],
        }),
        encoding="utf-8",
    )
    (doc_root / "metadata.json").write_text(
        json.dumps({"table_layout_file": str(layout_path)}),
        encoding="utf-8",
    )

    result = shard_document_table_layout("doc_001", tmp_path)

    assert result["already_sharded"] is True
    assert result["layout_count"] == 3
    assert not list(doc_root.glob("table_layout.backup-*.json"))
