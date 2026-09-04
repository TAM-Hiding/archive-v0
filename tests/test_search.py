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
