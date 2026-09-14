from flask import render_template

import app as app_module
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
    assert "Source Overview" in html
    assert "Refresh Search Index" in html
    assert "Remove Generated Notes" in html
    assert '<details class="technical-details">' in html
    assert "Re-index Generated" not in html
    assert "Open Generated Source View" not in html


def test_structural_reading_pages_use_shared_archive_theme():
    document = {
        "document": {"doc_id": "doc_001", "title": "Handbook"},
        "entries": [],
    }

    with app.test_request_context("/"):
        html = render_template("structural_index.html", document=document)

    assert "archive.css" in html
    assert "Browse Sections" in html
    assert 'class="back-menu" data-back-menu' in html


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


def test_empty_search_page_uses_subdued_secondary_actions_and_landing_offset():
    with app.test_request_context("/"):
        html = render_template(
            "index.html",
            query="",
            scope="all",
            results=[],
            expanded_terms=[],
            message="",
        )

    assert "search-shell-idle" in html
    assert 'class="search-actions"' in html
    assert 'value="search" class="button-primary"' in html
    assert 'value="reload" class="button-secondary"' in html
    assert 'href="/add" class="button-secondary"' in html
    assert 'href="/curator" class="button-secondary"' in html


def test_add_note_uses_shared_theme_and_navigation():
    with app.test_request_context("/"):
        html = render_template("add_note.html", folder_tree={})

    assert "archive.css" in html
    assert 'class="back-menu" data-back-menu' in html
    assert 'class="note-form"' in html
    assert 'class="button-primary">Save Note' in html
    assert 'class="button-secondary">Cancel' in html


def test_curator_launch_and_document_open_controls_are_subdued_buttons():
    document = {
        "doc_id": "doc_001",
        "title": "Handbook",
        "source_filename": "handbook.pdf",
        "category_path": "reference",
        "status": "chunked",
        "page_count": 10,
        "structural_index_entry_count": 8,
        "chunk_count": 8,
        "chunk_storage_mode": "structural_only",
        "chunk_count_estimate": 8,
        "has_generated_output": True,
        "updated_at": "2026-09-12",
    }

    with app.test_request_context("/"):
        dashboard = render_template("curator_dashboard.html")
        documents = render_template("curator_documents.html", documents=[document])

    assert 'href="/curator/notes" class="button-secondary"' in dashboard
    assert 'href="/curator/documents" class="button-secondary"' in dashboard
    assert 'href="/curator/document/doc_001" class="button-secondary">Open' in documents


def test_search_results_do_not_keep_landing_page_offset():
    note = {
        "id": 0,
        "title": "Result",
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
            query="result",
            scope="all",
            results=[(1, note, "Result preview")],
            expanded_terms=["result"],
            message="",
        )

    opening_shell = html.split(">", 2)[2]
    assert 'class="container search-shell"' in opening_shell
    assert 'class="container search-shell search-shell-idle"' not in html


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
    assert 'class="button-secondary">Open' in html
    assert 'class="button-secondary">Edit' in html
    assert 'class="button-secondary">Delete' in html


def test_notes_curator_defaults_to_manual_and_can_show_generated(
    monkeypatch,
):
    manual_note = {
        "id": 1,
        "title": "Fixture Setup",
        "body": "Manual shop note.",
        "relative_path": "shop/fixture.md",
        "category": "shop",
        "category_parts": ["shop"],
        "tags": [],
        "aliases": [],
        "meta": {},
        "is_generated": False,
        "note_origin": "manual",
    }
    generated_note = {
        "id": 2,
        "title": "Short Reference Chunk",
        "body": "Generated source content.",
        "relative_path": "_generated/reference/chunk.md",
        "category": "_generated > reference",
        "category_parts": ["_generated", "reference"],
        "tags": ["generated"],
        "aliases": [],
        "meta": {"source_doc_id": "doc_001", "chunk_index": "0"},
        "is_generated": True,
        "note_origin": "generated",
    }
    monkeypatch.setattr(app_module, "refresh_archive", lambda: None)
    monkeypatch.setattr(app_module, "notes", [manual_note, generated_note])

    client = app.test_client()
    manual_html = client.get("/curator/notes").get_data(as_text=True)
    generated_html = client.get(
        "/curator/notes?view=generated"
    ).get_data(as_text=True)

    assert "Fixture Setup" in manual_html
    assert "Short Reference Chunk" not in manual_html
    assert "Short Reference Chunk" in generated_html
    assert "Fixture Setup" not in generated_html
    assert "Generated <span class=\"filter-count\">1</span>" in generated_html


def test_search_result_actions_use_sage_button_components():
    note = {
        "id": 4,
        "title": "Fixture Setup",
        "tags": [],
        "tags_display": "—",
        "aliases": [],
        "category": "shop",
        "is_generated": False,
        "meta": {},
    }

    with app.test_request_context("/"):
        html = render_template(
            "index.html",
            query="fixture",
            scope="notes",
            results=[(5, note, "Clamp before indicating.")],
            expanded_terms=["fixture"],
            message="",
        )

    assert 'class="result-title-link"' in html
    assert 'class="button-secondary button-compact">Edit</a>' in html
    assert "[Edit]" not in html
    assert ">Manual Notes</option>" in html
    assert ">Generated Sources</option>" in html


def test_individual_note_and_edit_pages_use_shared_theme():
    note = {
        "id": 4,
        "title": "Fixture Setup",
        "body": "Clamp before indicating.",
        "tags": [],
        "aliases": [],
        "category": "shop",
        "path": "notes/shop/fixture_setup.md",
    }

    with app.test_request_context("/"):
        note_html = render_template("note.html", note=note)
        edit_html = render_template("edit_note.html", note=note)

    assert "archive.css" in note_html
    assert 'class="back-menu" data-back-menu' in note_html
    assert 'class="body note-body"' in note_html
    assert "Tags:" not in note_html
    assert "archive.css" in edit_html
    assert 'class="note-form"' in edit_html
    assert 'class="button-primary">Save Changes' in edit_html


def test_legacy_context_and_editor_confirmation_use_shared_theme():
    context = {"previous": None, "current": None, "next": None}
    note = {"id": 2, "path": "notes/example.md"}

    with app.test_request_context("/"):
        context_html = render_template("source_context.html", context=context)
        launched_html = render_template("edit_launched.html", note=note)

    assert "archive.css" in context_html
    assert 'class="back-menu" data-back-menu' in context_html
    assert "archive.css" in launched_html
    assert "Back to Note" in launched_html


def test_back_control_uses_history_with_an_accessible_destination_toggle():
    with app.test_request_context("/"):
        html = render_template("partials/back_menu.html")

    assert 'class="back-button" data-history-back' in html
    assert "window.history.back()" in html
    assert 'class="back-menu-toggle"' in html
    assert 'aria-expanded="false"' in html
    assert 'aria-controls="archive-back-destinations"' in html
    assert 'aria-label="Back destinations"' in html
