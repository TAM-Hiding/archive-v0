import archive


def test_structural_segment_uses_verified_source_span(tmp_path, monkeypatch):
    cleaned_text = "Unrelated prefix.\nCorrect complete segment body.\nTrailing text."
    cleaned_text_file = tmp_path / "cleaned_text.txt"
    cleaned_text_file.write_text(cleaned_text, encoding="utf-8")
    expected_body = "Correct complete segment body."
    source_start = cleaned_text.index(expected_body)

    monkeypatch.setattr(
        archive,
        "get_structural_index_for_document",
        lambda doc_id: {
            "document": {
                "doc_id": doc_id,
                "cleaned_text_file": str(cleaned_text_file),
            },
            "entries": [
                {
                    "entry_index": 0,
                    "preview": "Correct complete...",
                    "source_char_start": source_start,
                    "source_char_end": source_start + len(expected_body),
                }
            ],
        },
    )

    segment = archive.get_structural_segment("doc_001", 0)

    assert segment["current"]["body"] == expected_body


def test_legacy_logical_offsets_fall_back_to_matching_preview(
    tmp_path,
    monkeypatch,
):
    cleaned_text_file = tmp_path / "cleaned_text.txt"
    cleaned_text_file.write_text(
        "Unrelated numeric table data that must not be displayed.",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        archive,
        "get_structural_index_for_document",
        lambda doc_id: {
            "document": {
                "doc_id": doc_id,
                "cleaned_text_file": str(cleaned_text_file),
            },
            "entries": [
                {
                    "entry_index": 0,
                    "preview": "The correct hypoid bevel gear preview...",
                    "char_start": 0,
                    "char_end": 20,
                }
            ],
        },
    )

    segment = archive.get_structural_segment("doc_001", 0)

    assert segment["current"]["body"] == (
        "The correct hypoid bevel gear preview..."
    )
