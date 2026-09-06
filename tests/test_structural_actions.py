from flask import render_template

from app import app


def test_structural_search_hit_uses_document_routes_not_synthetic_note_id():
    note = {
        "id": "structural:doc_001:7",
        "title": "WOODRUFF KEYS",
        "tags_display": "—",
        "aliases": [],
        "aliases_display": "—",
        "category": "reference > machining",
        "is_generated": True,
        "meta": {
            "structural_hit": True,
            "source_doc_id": "doc_001",
            "entry_index": 7,
        },
    }

    with app.test_request_context("/"):
        html = render_template(
            "index.html",
            query="woodruff",
            scope="reference",
            results=[(5, note, "Woodruff key dimensions")],
            expanded_terms=["woodruff"],
            message="",
        )

    entry_url = "/curator/document/doc_001/structure/7"

    assert f'href="{entry_url}"' in html
    assert 'href="/curator/document/doc_001"' in html
    assert 'href="/curator/document/doc_001/source"' in html
    assert "[Context]" in html
    assert "[Source]" in html
    assert "[Edit]" not in html
    assert "/edit/structural:doc_001:7" not in html
    assert "/context/structural:doc_001:7" not in html
    assert "/source/structural:doc_001:7" not in html
