import json
from pathlib import Path

import extract_table_layout as command


def test_extract_document_table_layout_writes_sidecar_and_links_entries(
    tmp_path,
    monkeypatch,
):
    doc_root = tmp_path / "doc_001"
    doc_root.mkdir()
    source_path = doc_root / "source.pdf"
    source_path.write_bytes(b"test pdf placeholder")
    structural_index_path = doc_root / "structural_index.json"
    structural_index_path.write_text(
        json.dumps([
            {
                "entry_index": 4,
                "content_type": "table",
                "page_start": 8,
                "table_caption": "Table 6. Metric Woodruff Keys",
                "search_text": "Original flattened table text.",
            },
            {
                "entry_index": 5,
                "content_type": "prose",
                "page_start": 9,
                "search_text": "",
            },
        ]),
        encoding="utf-8",
    )
    metadata_path = doc_root / "metadata.json"
    metadata_path.write_text(
        json.dumps({
            "doc_id": "doc_001",
            "stored_source_filename": "source.pdf",
            "source_filename": "handbook.pdf",
            "structural_index_file": str(structural_index_path),
        }),
        encoding="utf-8",
    )

    captured_pages = None

    def fake_extract(_source_path, page_numbers):
        nonlocal captured_pages
        captured_pages = page_numbers
        return [{
            "layout_id": "page_0008_table_01",
            "page_number": 8,
            "caption": "Table 6. Metric Woodruff Keys",
            "caption_key": "table 6 metric woodruff keys",
            "reading_order_text": "Key size | Width | Depth",
        }]

    monkeypatch.setattr(command, "extract_pdf_table_layouts", fake_extract)

    result = command.extract_document_table_layout("doc_001", tmp_path)

    assert captured_pages == {8}
    assert result["table_layout_count"] == 1
    assert result["linked_entry_count"] == 1
    assert (doc_root / "table_layout.json").is_file()

    entries = json.loads(structural_index_path.read_text(encoding="utf-8"))
    assert entries[0]["table_layout_id"] == "page_0008_table_01"
    assert "Original flattened table text." in entries[0]["search_text"]
    assert "Key size | Width | Depth" in entries[0]["search_text"]
    assert "table_layout_id" not in entries[1]

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["table_layout_count"] == 1
    assert metadata["table_layout_linked_entry_count"] == 1
    assert list(doc_root.glob("metadata.backup-*.json"))
    assert list(doc_root.glob("structural_index.backup-*.json"))


def test_extract_document_table_layout_rejects_non_plain_doc_id(tmp_path):
    try:
        command.extract_document_table_layout("../doc_001", tmp_path)
    except ValueError as error:
        assert "plain directory name" in str(error)
    else:
        raise AssertionError("expected invalid doc_id to be rejected")


def test_targeted_pilot_preserves_other_shards_and_repairs_legacy_entries(tmp_path, monkeypatch):
    folder = tmp_path / "doc"
    folder.mkdir()
    (folder / "source.pdf").write_bytes(b"unchanged source")
    index = folder / "structural_index.json"
    caption = "Prime Number and Factor Table for 1 to 1199"
    index.write_text(json.dumps([
        {"content_type": "prose", "page_start": 31, "preview": caption + " From 0 100",
         "source_char_start": 150, "source_char_end": 300, "semantic_unit_id": "stable-unit"},
        {"content_type": "table", "page_start": 100, "table_layout_id": "old_other"},
    ]))
    layout_file = folder / "table_layout.json"
    command.write_sharded_table_layout_store(layout_file, {"layouts": [
        {"layout_id": "old_other", "page_number": 100, "grid": [["keep this"]]},
        {"layout_id": "page_0031_table_01", "page_number": 31, "grid": [["old packed rows"]]},
    ]})
    other_before = (folder / "table_layouts" / "old_other.json").read_bytes()
    metadata = folder / "metadata.json"
    metadata.write_text(json.dumps({"doc_id": "doc", "stored_source_filename": "source.pdf",
                                   "structural_index_file": str(index),
                                   "table_layout_file": str(layout_file)}))
    def extract(source, page_numbers):
        assert page_numbers == {31}
        return [{"layout_id": "page_0031_table_01", "page_number": 31,
                 "caption": caption, "caption_key": caption.casefold(),
                 "grid": [["recovered"]], "reading_order_text": "recovered"}]
    monkeypatch.setattr(command, "extract_pdf_table_layouts", extract)
    result = command.extract_document_table_layout("doc", tmp_path, page_numbers=[31])
    assert result["table_layout_count"] == 2
    assert (folder / "table_layouts" / "old_other.json").read_bytes() == other_before
    entries = json.loads(index.read_text())
    assert entries[0]["content_type"] == "table"
    assert entries[0]["table_layout_id"] == "page_0031_table_01"
    assert entries[0]["source_char_start"] == 150
    assert entries[0]["source_char_end"] == 300
    assert entries[0]["semantic_unit_id"] == "stable-unit"
    assert entries[1]["table_layout_id"] == "old_other"
    backup = Path(result["table_shard_backup_directory"]) / "page_0031_table_01.json"
    assert "old packed rows" in backup.read_text()
    assert (folder / "source.pdf").read_bytes() == b"unchanged source"
