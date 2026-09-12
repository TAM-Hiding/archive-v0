import json

import reextract_structure


def test_reextract_structural_document_rebuilds_in_place_with_backups(
    tmp_path,
    monkeypatch,
):
    doc_root = tmp_path / "doc_001"
    doc_root.mkdir()
    (doc_root / "source.pdf").write_bytes(b"source placeholder")
    extracted_path = doc_root / "extracted_text.txt"
    cleaned_path = doc_root / "cleaned_text.txt"
    structural_path = doc_root / "structural_index.json"
    extracted_path.write_text("old extracted", encoding="utf-8")
    cleaned_path.write_text("old cleaned", encoding="utf-8")
    structural_path.write_text("[]", encoding="utf-8")
    metadata_path = doc_root / "metadata.json"
    metadata_path.write_text(
        json.dumps({
            "doc_id": "doc_001",
            "chunk_storage_mode": "structural_only",
            "stored_source_filename": "source.pdf",
            "extracted_text_file": str(extracted_path),
            "cleaned_text_file": str(cleaned_path),
            "structural_index_file": str(structural_path),
            "metadata_file": str(metadata_path),
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        reextract_structure,
        "extract_text_from_pdf",
        lambda path, extractor: {
            "extractor": extractor,
            "page_count": 1,
            "text": "--- PAGE 1 ---\nGeometry ordered equation.",
        },
    )
    monkeypatch.setattr(
        reextract_structure,
        "build_chunks",
        lambda doc_id, text: [{
            "chunk_index": 1,
            "page_start": 1,
            "page_end": 1,
            "text": "Geometry ordered equation.",
        }],
    )
    monkeypatch.setattr(
        reextract_structure,
        "index_structural_doc_to_generated_note",
        lambda path: {"note_count": 1},
    )

    result = reextract_structure.reextract_structural_document(
        "doc_001",
        tmp_path,
    )

    assert result["extractor"] == "pdfplumber"
    assert result["chunk_count"] == 1
    assert "Geometry ordered equation." in extracted_path.read_text(
        encoding="utf-8"
    )
    assert "Geometry ordered equation." in cleaned_path.read_text(
        encoding="utf-8"
    )
    assert list(doc_root.glob("extracted_text.backup-*.txt"))
    assert list(doc_root.glob("cleaned_text.backup-*.txt"))
    assert list(doc_root.glob("structural_index.backup-*.json"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["extractor"] == "pdfplumber"
    assert metadata["chunk_count"] == 1


def test_reextract_structural_document_rejects_persistent_mode(tmp_path):
    doc_root = tmp_path / "doc_001"
    doc_root.mkdir()
    (doc_root / "metadata.json").write_text(
        json.dumps({"chunk_storage_mode": "persistent"}),
        encoding="utf-8",
    )

    try:
        reextract_structure.reextract_structural_document("doc_001", tmp_path)
    except ValueError as error:
        assert "structural-only" in str(error)
    else:
        raise AssertionError("expected persistent document to be rejected")
