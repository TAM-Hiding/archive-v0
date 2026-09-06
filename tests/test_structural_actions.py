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


def test_semantic_context_template_renders_children_and_highlights_match():
    segment = {
        "document": {
            "doc_id": "doc_001",
            "title": "Machinery's Handbook",
        },
        "context_mode": "semantic_unit",
        "matched_entry_index": 8,
        "semantic_unit": {
            "page_start": 100,
            "page_end": 102,
            "char_count": 2400,
            "retrieval_chunk_count": 2,
            "section_heading": "GEARS AND GEARING",
            "subheading": "Hypoid Bevel Gears",
        },
        "context_entries": [
            {
                "entry_index": 7,
                "entry": {
                    "chunk_index": 8,
                    "retrieval_chunk_index": 1,
                    "retrieval_chunk_count": 2,
                    "page_start": 100,
                    "page_end": 101,
                    "char_count": 1200,
                    "section_heading": "GEARS AND GEARING",
                },
                "body": "First semantic child.",
            },
            {
                "entry_index": 8,
                "entry": {
                    "chunk_index": 9,
                    "retrieval_chunk_index": 2,
                    "retrieval_chunk_count": 2,
                    "page_start": 102,
                    "page_end": 102,
                    "char_count": 1200,
                    "section_heading": "GEARS AND GEARING",
                },
                "body": "Matched semantic child.",
            },
        ],
        "previous": None,
        "current": None,
        "next": None,
    }

    with app.test_request_context("/"):
        html = render_template("structural_segment.html", segment=segment)

    assert "Semantic Context" in html
    assert "Hypoid Bevel Gears" in html
    assert "Pages 100–102" in html
    assert "First semantic child." in html
    assert "Matched semantic child." in html
    normalized_html = " ".join(html.split())
    assert "Matched Entry 8" in normalized_html
    assert 'class="segment current"' in html
