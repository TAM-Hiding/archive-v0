from archive import build_vocabulary, search_notes


def make_note(
    title,
    body="",
    tags=None,
    aliases=None,
    path="notes/test.md",
    generated=False,
    source_doc_id="",
):
    tags = tags or []
    aliases = aliases or []

    return {
        "id": 0,
        "title": title,
        "title_search": title.lower(),
        "tags": [tag.lower() for tag in tags],
        "aliases": [alias.lower() for alias in aliases],
        "meta": {
            "source_doc_id": source_doc_id,
        },
        "body": body,
        "body_search": body.lower(),
        "path": path,
        "relative_path": path,
        "path_search": path.lower().replace("_", " "),
        "category": "",
        "category_parts": [],
        "is_generated": generated,
    }


def test_title_match_ranks_above_body_match():
    notes = [
        make_note(
            title="Compass Calibration",
            body="General setup information.",
            path="notes/compass.md",
        ),
        make_note(
            title="Sensor Notes",
            body="The compass requires calibration.",
            path="notes/sensors.md",
        ),
    ]

    vocabulary = build_vocabulary(notes)
    results, _ = search_notes("compass", notes, vocabulary)

    assert results[0][1]["title"] == "Compass Calibration"
    assert results[0][0] > results[1][0]


def test_alias_match_is_searchable():
    notes = [
        make_note(
            title="BerryIMU Calibration",
            aliases=["magnetometer"],
            path="notes/berryimu.md",
        ),
        make_note(
            title="Unrelated Sensor",
            body="Temperature and humidity.",
            path="notes/environment.md",
        ),
    ]

    vocabulary = build_vocabulary(notes)
    results, _ = search_notes("magnetometer", notes, vocabulary)

    assert len(results) == 1
    assert results[0][1]["title"] == "BerryIMU Calibration"


def test_long_typo_uses_fuzzy_expansion():
    notes = [
        make_note(
            title="Compass Calibration",
            path="notes/compass.md",
        ),
    ]

    vocabulary = build_vocabulary(notes)
    results, expanded_terms = search_notes("compas", notes, vocabulary)

    assert "compass" in expanded_terms
    assert results[0][1]["title"] == "Compass Calibration"


def test_generated_chunks_do_not_swamp_handwritten_note():
    notes = [
        make_note(
            title="Battery Notes",
            body="battery",
            path="notes/battery.md",
        ),
    ]

    for index in range(5):
        notes.append(
            make_note(
                title=f"Reference Chunk {index}",
                body="battery",
                path=f"notes/_generated/manual/chunk_{index}.md",
                generated=True,
                source_doc_id="manual_001",
            )
        )

    vocabulary = build_vocabulary(notes)
    results, _ = search_notes("battery", notes, vocabulary)

    result_titles = [note["title"] for _, note in results]

    assert "Battery Notes" in result_titles
    assert results[0][1]["title"] == "Battery Notes"


def test_search_scope_filters_notes_and_reference():
    notes = [
        make_note(
            title="Handwritten Battery Note",
            body="battery",
            path="notes/battery.md",
        ),
        make_note(
            title="Battery Manual",
            body="battery",
            path="notes/_generated/manual/chunk_1.md",
            generated=True,
            source_doc_id="manual_001",
        ),
    ]

    vocabulary = build_vocabulary(notes)

    note_results, _ = search_notes(
        "battery",
        notes,
        vocabulary,
        scope="notes",
    )

    reference_results, _ = search_notes(
        "battery",
        notes,
        vocabulary,
        scope="reference",
    )

    assert len(note_results) == 1
    assert note_results[0][1]["title"] == "Handwritten Battery Note"

    assert len(reference_results) == 1
    assert reference_results[0][1]["title"] == "Battery Manual"


def test_manual_scope_excludes_system_notes():
    manual = make_note(title="Shop Setup", body="fixture")
    system = make_note(title="System Setup", body="fixture")
    system["category_parts"] = ["_system"]

    notes = [manual, system]
    results, _ = search_notes(
        "fixture",
        notes,
        build_vocabulary(notes),
        scope="notes",
    )

    assert [note["title"] for _, note in results] == ["Shop Setup"]


def test_explicit_page_query_uses_generated_note_page_metadata():
    page_17 = make_note(
        title="Page words",
        body="See page for additional information.",
        generated=True,
    )
    page_17["meta"].update({"page_start": "17", "page_end": "17"})
    page_263 = make_note(
        title="Target page",
        body="Recovered handbook content.",
        generated=True,
    )
    page_263["meta"].update({"page_start": "262", "page_end": "264"})

    notes = [page_17, page_263]
    results, expanded_terms = search_notes(
        "page 263",
        notes,
        build_vocabulary(notes),
        scope="reference",
    )

    assert [note["title"] for _, note in results] == ["Target page"]
    assert expanded_terms == []

def test_structural_index_entries_are_searchable(tmp_path, monkeypatch):
    import json
    import archive

    doc_root = tmp_path / "doc_001"
    doc_root.mkdir()

    structural_index_file = doc_root / "structural_index.json"
    structural_index_file.write_text(
        json.dumps(
            [
                {
                    "entry_index": 0,
                    "chunk_index": 1,
                    "page_start": 42,
                    "page_end": 42,
                    "section_heading": "WOODRUFF KEYS",
                    "char_count": 500,
                    "char_start": 1000,
                    "char_end": 1500,
                    "preview": "Dimensions and tolerances for Woodruff keys and keyseats.",
                }
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        archive,
        "list_ingested_documents",
        lambda: [
            {
                "doc_id": "doc_001",
                "title": "Machinery's Handbook",
                "source_filename": "Machinery.pdf",
                "category_path": "reference/machining",
                "chunk_storage_mode": "structural_only",
                "structural_index_file": str(structural_index_file),
            }
        ],
    )

    results = archive.search_structural_entries("woodruff")

    assert len(results) == 1

    score, result = results[0]

    assert score > 0
    assert result["meta"]["source_doc_id"] == "doc_001"
    assert result["meta"]["entry_index"] == 0
    assert result["meta"]["page_start"] == 42
    assert result["meta"]["structural_hit"] is True
    assert "woodruff" in result["body_search"]


def test_structural_page_query_returns_only_the_requested_page(
    tmp_path,
    monkeypatch,
):
    import json
    import archive

    structural_index_file = tmp_path / "structural_index.json"
    structural_index_file.write_text(
        json.dumps([
            {
                "entry_index": 0,
                "chunk_index": 1,
                "page_start": 17,
                "page_end": 17,
                "section_heading": "Page References",
                "preview": "See page 263 for another topic.",
            },
            {
                "entry_index": 1,
                "chunk_index": 2,
                "page_start": 263,
                "page_end": 263,
                "section_heading": "Target Section",
                "preview": "The requested page content.",
            },
        ]),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        archive,
        "list_ingested_documents",
        lambda: [{
            "doc_id": "doc_001",
            "title": "Machinery's Handbook",
            "source_filename": "Machinery.pdf",
            "category_path": "reference/machining",
            "chunk_storage_mode": "structural_only",
            "structural_index_file": str(structural_index_file),
        }],
    )

    results = archive.search_structural_entries("page 263")

    assert len(results) == 1
    assert results[0][1]["meta"]["entry_index"] == 1
    assert results[0][1]["meta"]["page_start"] == 263


def test_structural_table_search_uses_caption_and_full_table_text(
    tmp_path,
    monkeypatch,
):
    import json
    import archive

    structural_index_file = tmp_path / "structural_index.json"
    structural_index_file.write_text(
        json.dumps([
            {
                "entry_index": 0,
                "chunk_index": 1,
                "page_start": 2499,
                "page_end": 2499,
                "section_heading": "Advantages of Woodruff Keys",
                "content_type": "table",
                "retrieval_chunk_index": 1,
                "retrieval_chunk_count": 2,
                "table_caption": (
                    "Table 6. Keyway Dimensions for Metric Woodruff Keys"
                ),
                "preview": "Table headers appear here.",
                "search_text": "Table 6. Metric Woodruff table headers.",
            },
            {
                "entry_index": 1,
                "chunk_index": 2,
                "page_start": 2499,
                "page_end": 2499,
                "section_heading": "Advantages of Woodruff Keys",
                "content_type": "table",
                "retrieval_chunk_index": 2,
                "retrieval_chunk_count": 2,
                "table_caption": (
                    "Table 6. Keyway Dimensions for Metric Woodruff Keys"
                ),
                "preview": "Later table rows appear here.",
                "search_text": "Later rows contain deepvalue data.",
            },
        ]),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        archive,
        "list_ingested_documents",
        lambda: [{
            "doc_id": "doc_001",
            "title": "Machinery's Handbook",
            "source_filename": "Machinery.pdf",
            "category_path": "reference/machining",
            "chunk_storage_mode": "structural_only",
            "structural_index_file": str(structural_index_file),
        }],
    )

    results = archive.search_structural_entries("deepvalue")

    assert len(results) == 1
    _, result = results[0]
    assert result["title"].startswith("Table 6.")
    assert result["meta"]["content_type"] == "table"
    assert "deepvalue" in result["body"]
    assert "deepvalue" in result["body_search"]

    caption_results = archive.search_structural_entries("metric")

    assert len(caption_results) == 1
    assert caption_results[0][1]["meta"]["entry_index"] == 0


def test_structural_search_coalesces_hits_from_one_table_unit(
    tmp_path,
    monkeypatch,
):
    import json
    import archive

    structural_index_file = tmp_path / "structural_index.json"
    structural_index_file.write_text(
        json.dumps([
            {
                "entry_index": 0,
                "chunk_index": 1,
                "semantic_unit_id": "doc_001_unit_0001",
                "page_start": 15,
                "page_end": 15,
                "section_heading": "Decimal Equivalents",
                "content_type": "table",
                "table_caption": "Table 1. Fractional and Decimal Inch",
                "preview": "sharedvalue first rows",
                "search_text": "sharedvalue first rows",
            },
            {
                "entry_index": 1,
                "chunk_index": 2,
                "semantic_unit_id": "doc_001_unit_0001",
                "page_start": 15,
                "page_end": 15,
                "section_heading": "Decimal Equivalents",
                "content_type": "table",
                "table_caption": "Table 1. Fractional and Decimal Inch",
                "preview": "sharedvalue later rows",
                "search_text": "sharedvalue later rows",
            },
        ]),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        archive,
        "list_ingested_documents",
        lambda: [{
            "doc_id": "doc_001",
            "title": "Machinery's Handbook",
            "source_filename": "Machinery.pdf",
            "category_path": "reference/machining",
            "chunk_storage_mode": "structural_only",
            "structural_index_file": str(structural_index_file),
        }],
    )

    results = archive.search_structural_entries("sharedvalue")

    assert len(results) == 1
    assert results[0][1]["meta"]["semantic_unit_id"] == "doc_001_unit_0001"


def test_structural_search_includes_figure_labels_without_losing_preview(
    tmp_path,
    monkeypatch,
):
    import json
    import archive

    structural_index_file = tmp_path / "structural_index.json"
    structural_index_file.write_text(
        json.dumps([{
            "entry_index": 0,
            "chunk_index": 1,
            "page_start": 754,
            "page_end": 754,
            "section_heading": "Outside Micrometer Caliper",
            "preview": "The frame supports the micrometer spindle.",
            "search_text": "",
            "figure_search_text": "Anvil Barrel Thimble Graduations",
            "figure_layout_ids": ["page_0754_figure_01"],
        }]),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        archive,
        "list_ingested_documents",
        lambda: [{
            "doc_id": "doc_001",
            "title": "Handbook",
            "source_filename": "handbook.pdf",
            "category_path": "reference/machining",
            "chunk_storage_mode": "structural_only",
            "structural_index_file": str(structural_index_file),
        }],
    )

    results = archive.search_structural_entries("graduations")

    assert len(results) == 1
    body = results[0][1]["body"]
    assert "frame supports" in body
    assert "Graduations" in body
    assert results[0][1]["meta"]["figure_layout_ids"] == [
        "page_0754_figure_01"
    ]
