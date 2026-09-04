from pathlib import Path

from ingestion.registry import create_document_record


def test_create_document_record(tmp_path):
    source_file = tmp_path / "sample.pdf"
    source_file.write_bytes(b"%PDF-1.4\n% fake test pdf\n")

    metadata = create_document_record(
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
