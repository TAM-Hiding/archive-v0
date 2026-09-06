import json

import rebuild_structure


def test_rebuild_structural_document_updates_in_place_with_backups(
    tmp_path,
    monkeypatch,
):
    doc_id = "doc_001"
    documents_root = tmp_path / "documents"
    doc_root = documents_root / doc_id
    doc_root.mkdir(parents=True)

    cleaned_text_path = doc_root / "cleaned_text.txt"
    cleaned_text = (
        "--- PAGE 1 ---\n"
        "INTRODUCTION\n"
        "Correct source-anchored body.\n"
    )
    cleaned_text_path.write_text(cleaned_text, encoding="utf-8")

    metadata_path = doc_root / "metadata.json"
    metadata_path.write_text(
        json.dumps(
            {
                "doc_id": doc_id,
                "title": "Test Document",
                "source_filename": "test.pdf",
                "category_path": "reference/testing",
                "chunk_storage_mode": "structural_only",
                "cleaned_text_file": str(cleaned_text_path),
                "chunk_count": 999,
            }
        ),
        encoding="utf-8",
    )

    structural_index_path = doc_root / "structural_index.json"
    structural_index_path.write_text(
        json.dumps([{"preview": "Old incorrect entry."}]),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        rebuild_structure,
        "index_structural_doc_to_generated_note",
        lambda metadata_file: {"note_count": 1},
    )

    result = rebuild_structure.rebuild_structural_document(
        doc_id,
        documents_root=documents_root,
    )

    rebuilt_entries = json.loads(
        structural_index_path.read_text(encoding="utf-8")
    )
    rebuilt_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert result["doc_id"] == doc_id
    assert result["chunk_count"] == 1
    assert rebuilt_entries[0]["preview"] == "Correct source-anchored body."
    assert rebuilt_entries[0]["source_char_start"] is not None
    assert rebuilt_entries[0]["source_char_end"] is not None
    assert rebuilt_metadata["chunk_count"] == 1
    assert rebuilt_metadata["structural_index_entry_count"] == 1
    assert rebuilt_metadata["structure_rebuilt_at"]
    assert list(doc_root.glob("metadata.backup-*.json"))
    assert list(doc_root.glob("structural_index.backup-*.json"))


def test_rebuild_rejects_non_structural_document(tmp_path):
    doc_id = "doc_001"
    doc_root = tmp_path / "documents" / doc_id
    doc_root.mkdir(parents=True)
    (doc_root / "metadata.json").write_text(
        json.dumps(
            {
                "doc_id": doc_id,
                "chunk_storage_mode": "persistent",
            }
        ),
        encoding="utf-8",
    )

    try:
        rebuild_structure.rebuild_structural_document(
            doc_id,
            documents_root=tmp_path / "documents",
        )
    except ValueError as error:
        assert "structural-only" in str(error)
    else:
        raise AssertionError("Expected non-structural rebuild to be rejected")
