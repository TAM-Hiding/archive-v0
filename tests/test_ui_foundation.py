from flask import render_template

from app import app


def test_document_page_uses_plain_language_actions_and_collapsed_details():
    document = {
        "doc_id": "doc_001",
        "title": "Machinery's Handbook",
        "source_filename": "machinery.pdf",
        "category_path": "reference/machining",
        "status": "chunked",
        "chunk_count": 100,
        "page_count": 25,
        "has_generated_output": True,
        "created_at": "2026-09-01",
        "updated_at": "2026-09-02",
        "chunk_storage_mode": "structural_only",
        "chunk_count_estimate": 100,
        "structural_index_entry_count": 90,
        "promoted_chunk_count": 0,
        "metadata_file": "metadata.json",
        "doc_root": "documents/doc_001",
        "generated_output_dir": "notes/generated",
        "structural_index_file": "structural_index.json",
    }

    with app.test_request_context("/"):
        html = render_template("curator_document.html", document=document)

    assert "Browse Sections" in html
    assert "Read Extracted Text" in html
    assert "Refresh Search Index" in html
    assert "Remove Generated Notes" in html
    assert '<details class="technical-details">' in html
    assert "Re-index Generated" not in html
    assert "Open Generated Source View" not in html


def test_delete_note_result_returns_to_notes_curator():
    with app.test_request_context("/"):
        html = render_template(
            "curator_action_result.html",
            title="Delete Note",
            result={"ok": True, "message": "Note deleted."},
            document=None,
            primary_return_url="/curator/notes",
            primary_return_label="Back to Notes",
        )

    assert 'href="/curator/notes"' in html
    assert "Back to Notes" in html


def test_search_result_hides_empty_tags():
    note = {
        "id": 0,
        "title": "Untagged Note",
        "tags": [],
        "tags_display": "—",
        "aliases": [],
        "category": "notes",
        "is_generated": False,
        "meta": {},
    }

    with app.test_request_context("/"):
        html = render_template(
            "index.html",
            query="note",
            scope="all",
            results=[(5, note, "A useful preview")],
            expanded_terms=["note"],
            message="",
        )

    assert "Score:" in html
    assert "Tags:" not in html


def test_notes_curator_card_leads_with_body_preview():
    note = {
        "id": 0,
        "title": "Shop Note",
        "body": "Remember the setup dimensions before cutting stock.",
        "relative_path": "notes/shop/setup.md",
        "category": "shop/setup",
        "tags": [],
        "aliases": [],
        "is_generated": False,
    }

    with app.test_request_context("/"):
        html = render_template("partials/note_card.html", note=note)

    assert "Remember the setup dimensions" in html
    assert '<summary>Details</summary>' in html
    assert "Tags:" not in html
