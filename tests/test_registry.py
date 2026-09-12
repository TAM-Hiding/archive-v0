from pathlib import Path

from ingestion import registry


def test_create_document_record(tmp_path, monkeypatch):
    notes_root = tmp_path / "notes"
    archive_data_root = notes_root / "_archive_data"
    documents_root = archive_data_root / "documents"
    monkeypatch.setattr(registry, "NOTES_ROOT", notes_root)
    monkeypatch.setattr(registry, "ARCHIVE_DATA_ROOT", archive_data_root)
    monkeypatch.setattr(registry, "DOCUMENTS_ROOT", documents_root)

    source_file = tmp_path / "sample.pdf"
    source_file.write_bytes(b"%PDF-1.4\n% fake test pdf\n")

    metadata = registry.create_document_record(
        str(source_file),
        "fiction/short_stories",
    )

    assert metadata["source_filename"] == "sample.pdf"
    assert metadata["category_path"] == "fiction/short_stories"
    assert metadata["file_type"] == "pdf"

    doc_root = Path(metadata["doc_root"])
    metadata_file = Path(metadata["metadata_file"])

    assert doc_root.exists()
    assert metadata_file.exists()
    assert doc_root.parent == documents_root
    assert (notes_root / "fiction" / "short_stories").is_dir()
