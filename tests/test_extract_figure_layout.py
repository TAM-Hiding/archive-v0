import json

import extract_figure_layout as command


def test_extract_document_figure_layout_writes_images_and_links_entries(
    tmp_path,
    monkeypatch,
):
    doc_root = tmp_path / "doc_001"
    doc_root.mkdir()
    (doc_root / "source.pdf").write_bytes(b"placeholder")
    cleaned_path = doc_root / "cleaned_text.txt"
    cleaned_path.write_text(
        "--- PAGE 754 ---\nFig. 1. Micrometer",
        encoding="utf-8",
    )
    index_path = doc_root / "structural_index.json"
    index_path.write_text(
        json.dumps([{
            "entry_index": 4,
            "page_start": 754,
            "preview": "Fig. 1. Micrometer",
        }]),
        encoding="utf-8",
    )
    metadata_path = doc_root / "metadata.json"
    metadata_path.write_text(
        json.dumps({
            "doc_id": "doc_001",
            "source_filename": "handbook.pdf",
            "stored_source_filename": "source.pdf",
            "cleaned_text_file": str(cleaned_path),
            "structural_index_file": str(index_path),
        }),
        encoding="utf-8",
    )

    def fake_extract(source, output_directory, page_numbers):
        image_path = output_directory / "page_0754_figure_01.png"
        output_directory.mkdir(parents=True)
        image_path.write_bytes(b"png")
        return [{
            "layout_id": "page_0754_figure_01",
            "page_number": 754,
            "figure_index": 1,
            "caption": "Fig. 1. Micrometer",
            "caption_key": "fig 1 micrometer",
            "bbox": [100, 80, 500, 220],
            "label_text": "Anvil Spindle Frame",
            "vector_object_count": 12,
            "embedded_image_count": 0,
            "image_filename": image_path.name,
        }]

    monkeypatch.setattr(command, "extract_pdf_figure_layouts", fake_extract)

    result = command.extract_document_figure_layout(
        "doc_001",
        tmp_path,
        page_numbers={754},
    )

    assert result["figure_layout_count"] == 1
    assert result["linked_figure_count"] == 1
    assert (doc_root / "figure_layout.json").is_file()
    assert (doc_root / "figure_layouts/page_0754_figure_01.png").is_file()
    entries = json.loads(index_path.read_text(encoding="utf-8"))
    assert entries[0]["figure_layout_ids"] == ["page_0754_figure_01"]
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["figure_layout_storage_mode"] == "image_shards"
    assert list(doc_root.glob("metadata.backup-*.json"))
