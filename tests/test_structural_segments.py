import archive


def test_table_layout_loader_reads_only_linked_shard(tmp_path):
    shard_directory = tmp_path / "table_layouts"
    shard_directory.mkdir()
    shard_path = shard_directory / "page_0008_table_01.json"
    shard_path.write_text(
        '{"layout_id":"page_0008_table_01","grid":[["Fit","Use"]]}',
        encoding="utf-8",
    )
    manifest_path = tmp_path / "table_layout.json"
    manifest_path.write_text(
        (
            '{"storage_mode":"sharded","layouts":['
            '{"layout_id":"page_0008_table_01",'
            '"file":"table_layouts/page_0008_table_01.json"}]}'
        ),
        encoding="utf-8",
    )

    result = archive.get_table_layout_for_entry(
        {"table_layout_file": str(manifest_path)},
        {"table_layout_id": "page_0008_table_01"},
    )

    assert result["grid"] == [["Fit", "Use"]]


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


def test_structural_segment_returns_complete_semantic_unit(
    tmp_path,
    monkeypatch,
):
    bodies = [
        "First page of the semantic unit.",
        "Matched middle page of the semantic unit.",
        "Final page of the semantic unit.",
        "A different semantic unit.",
    ]
    cleaned_text = "\n".join(bodies)
    cleaned_text_file = tmp_path / "cleaned_text.txt"
    cleaned_text_file.write_text(cleaned_text, encoding="utf-8")

    entries = []
    for index, body in enumerate(bodies):
        source_start = cleaned_text.index(body)
        semantic_unit_id = "doc_001_unit_0001" if index < 3 else "doc_001_unit_0002"
        entries.append({
            "entry_index": index,
            "chunk_index": index + 1,
            "semantic_unit_id": semantic_unit_id,
            "semantic_unit_index": 1 if index < 3 else 2,
            "semantic_unit_page_start": 10 if index < 3 else 13,
            "semantic_unit_page_end": 12 if index < 3 else 13,
            "semantic_unit_char_count": sum(len(item) for item in bodies[:3]),
            "semantic_unit_block_count": 3 if index < 3 else 1,
            "retrieval_chunk_index": index + 1 if index < 3 else 1,
            "retrieval_chunk_count": 3 if index < 3 else 1,
            "page_start": 10 + index,
            "page_end": 10 + index,
            "section_heading": "Discussion",
            "char_count": len(body),
            "source_char_start": source_start,
            "source_char_end": source_start + len(body),
            "preview": body[:12],
        })

    monkeypatch.setattr(
        archive,
        "get_structural_index_for_document",
        lambda doc_id: {
            "document": {
                "doc_id": doc_id,
                "cleaned_text_file": str(cleaned_text_file),
            },
            "entries": entries,
        },
    )

    segment = archive.get_structural_segment("doc_001", 1)

    assert segment["context_mode"] == "semantic_unit"
    assert segment["matched_entry_index"] == 1
    assert segment["semantic_unit"]["id"] == "doc_001_unit_0001"
    assert segment["semantic_unit"]["page_start"] == 10
    assert segment["semantic_unit"]["page_end"] == 12
    assert [
        item["body"]
        for item in segment["context_entries"]
    ] == bodies[:3]


def test_legacy_structural_index_keeps_neighbor_context(monkeypatch):
    monkeypatch.setattr(
        archive,
        "get_structural_index_for_document",
        lambda doc_id: {
            "document": {"doc_id": doc_id},
            "entries": [
                {"preview": "Previous legacy entry."},
                {"preview": "Current legacy entry."},
                {"preview": "Next legacy entry."},
            ],
        },
    )

    segment = archive.get_structural_segment("doc_001", 1)

    assert segment["context_mode"] == "legacy_neighbors"
    assert segment["context_entries"] == []
    assert segment["previous"]["body"] == "Previous legacy entry."
    assert segment["current"]["body"] == "Current legacy entry."
    assert segment["next"]["body"] == "Next legacy entry."
