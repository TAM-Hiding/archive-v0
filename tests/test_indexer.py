import json
from pathlib import Path

import ingestion.indexer as indexer


def test_index_chunks_to_generated_notes(tmp_path, monkeypatch):
    generated_root = tmp_path / "_generated"
    monkeypatch.setattr(indexer, "GENERATED_ROOT", generated_root)

    chunks_file = tmp_path / "chunks.json"
    metadata_file = tmp_path / "metadata.json"

    chunks = [
        {
            "chunk_index": 1,
            "semantic_unit_id": "test_doc_001_unit_0001",
            "semantic_unit_index": 1,
            "retrieval_chunk_index": 1,
            "retrieval_chunk_count": 1,
            "page_start": 1,
            "page_end": 1,
            "section_heading": "Introduction",
            "char_count": 24,
            "text": "This is the first chunk.",
        },
        {
            "chunk_index": 2,
            "page_start": 2,
            "page_end": 2,
            "section_heading": "Results",
            "char_count": 25,
            "text": "This is the second chunk.",
        },
    ]

    metadata = {
        "doc_id": "test_doc_001",
        "title": "Test Document",
        "source_filename": "test_document.pdf",
        "category_path": "reference/testing",
        "chunks_file": str(chunks_file),
    }

    chunks_file.write_text(
        json.dumps(chunks),
        encoding="utf-8",
    )

    metadata_file.write_text(
        json.dumps(metadata),
        encoding="utf-8",
    )

    result = indexer.index_chunks_to_generated_notes(metadata_file)

    assert result["doc_id"] == "test_doc_001"
    assert result["category_path"] == "reference/testing"
    assert result["note_count"] == 2

    output_dir = Path(result["output_dir"])

    assert output_dir.exists()
    assert output_dir.is_relative_to(generated_root)

    generated_files = [Path(path) for path in result["files"]]

    assert len(generated_files) == 2
    assert all(path.exists() for path in generated_files)

    first_note = generated_files[0].read_text(encoding="utf-8")

    assert "title: Test Document - chunk 0001" in first_note
    assert "source_doc_id: test_doc_001" in first_note
    assert "section_heading: Introduction" in first_note
    assert "semantic_unit_id: test_doc_001_unit_0001" in first_note
    assert "retrieval_chunk_index: 1" in first_note
    assert "retrieval_chunk_count: 1" in first_note
    assert "This is the first chunk." in first_note
