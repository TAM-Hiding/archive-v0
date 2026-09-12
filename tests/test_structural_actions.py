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


def test_semantic_context_template_preserves_equation_layout():
    segment = {
        "document": {"doc_id": "doc_001", "title": "Handbook"},
        "context_mode": "semantic_unit",
        "matched_entry_index": 4,
        "semantic_unit": {
            "page_start": 18,
            "page_end": 18,
            "char_count": 38,
            "retrieval_chunk_count": 1,
        },
        "context_entries": [{
            "entry_index": 4,
            "entry": {
                "chunk_index": 5,
                "retrieval_chunk_index": 1,
                "retrieval_chunk_count": 1,
                "page_start": 18,
                "page_end": 18,
                "char_count": 38,
                "layout_hint": "equation",
            },
            "body": "270 × 44\nx = --------\n      40",
        }],
        "table_layout": None,
        "table_layouts": [],
        "previous": None,
        "current": None,
        "next": None,
    }

    with app.test_request_context("/"):
        html = render_template("structural_segment.html", segment=segment)

    assert '<pre class="preview equation-preview">' in html
    assert "270 × 44\nx = --------\n      40" in html


def test_semantic_context_template_renders_recovered_figure():
    segment = {
        "document": {"doc_id": "doc_001", "title": "Handbook"},
        "context_mode": "semantic_unit",
        "matched_entry_index": 4,
        "semantic_unit": {
            "page_start": 754,
            "page_end": 754,
            "char_count": 100,
            "retrieval_chunk_count": 1,
        },
        "context_entries": [{
            "entry_index": 4,
            "entry": {
                "chunk_index": 5,
                "retrieval_chunk_index": 1,
                "retrieval_chunk_count": 1,
                "page_start": 754,
                "page_end": 754,
                "char_count": 100,
            },
            "body": "Micrometer discussion.",
        }],
        "figure_layouts": [{
            "layout_id": "page_0754_figure_01",
            "page_number": 754,
            "caption": "Fig. 1. Design features of a micrometer",
            "vector_object_count": 95,
            "embedded_image_count": 0,
        }],
        "table_layout": None,
        "table_layouts": [],
        "previous": None,
        "current": None,
        "next": None,
    }

    with app.test_request_context("/"):
        html = render_template("structural_segment.html", segment=segment)

    assert "Fig. 1. Design features of a micrometer" in html
    assert "/curator/document/doc_001/figure/page_0754_figure_01" in html
    assert "95 vector objects" in html


def test_semantic_context_template_identifies_table_unit():
    segment = {
        "document": {"doc_id": "doc_001", "title": "Handbook"},
        "context_mode": "semantic_unit",
        "matched_entry_index": 1,
        "semantic_unit": {
            "page_start": 2499,
            "page_end": 2499,
            "char_count": 1769,
            "retrieval_chunk_count": 1,
            "section_heading": "Advantages of Woodruff Keys",
            "subheading": None,
            "content_type": "table",
            "table_caption": "Table 6. Keyway Dimensions",
        },
        "context_entries": [{
            "entry_index": 1,
            "entry": {
                "chunk_index": 2,
                "retrieval_chunk_index": 1,
                "retrieval_chunk_count": 1,
                "page_start": 2499,
                "page_end": 2499,
                "char_count": 1769,
                "content_type": "table",
                "section_heading": "Advantages of Woodruff Keys",
            },
            "body": "Table 6. Keyway Dimensions",
        }],
        "previous": None,
        "current": None,
        "next": None,
    }

    with app.test_request_context("/"):
        html = render_template("structural_segment.html", segment=segment)

    assert "Table 6. Keyway Dimensions" in html
    normalized_html = " ".join(html.split())
    assert "1769 chars" in normalized_html
    assert "| Table | Advantages of Woodruff Keys" in normalized_html


def test_semantic_context_template_renders_linked_table_layout():
    segment = {
        "document": {"doc_id": "doc_001", "title": "Handbook"},
        "context_mode": "semantic_unit",
        "matched_entry_index": 1,
        "semantic_unit": {
            "page_start": 8,
            "page_end": 8,
            "char_count": 42,
            "retrieval_chunk_count": 1,
            "content_type": "table",
            "table_caption": "Table 1. Description of Preferred Fits",
        },
        "table_layout": {
            "caption": "Table 1. Description of Preferred Fits",
            "page_number": 8,
            "row_count": 2,
            "column_count": 2,
            "cells": [{}, {}, {}, {}],
            "grid": [
                ["Fit", "Description"],
                ["Running", "Parts move freely"],
            ],
            "reading_order_text": "Fit Description\nRunning Parts move freely",
        },
        "table_layouts": [{
            "caption": "Table 1. Description of Preferred Fits",
            "page_number": 8,
            "row_count": 2,
            "column_count": 2,
            "cells": [{}, {}, {}, {}],
            "grid": [
                ["Fit", "Description"],
                ["Running", "Parts move freely"],
            ],
            "reading_order_text": "Fit Description\nRunning Parts move freely",
        }],
        "context_entries": [{
            "entry_index": 1,
            "entry": {
                "chunk_index": 2,
                "retrieval_chunk_index": 1,
                "retrieval_chunk_count": 1,
                "page_start": 8,
                "page_end": 8,
                "char_count": 42,
                "content_type": "table",
                "section_heading": "Preferred Fits",
            },
            "body": "Table 1. Description of Preferred Fits",
        }],
        "previous": None,
        "current": None,
        "next": None,
    }

    with app.test_request_context("/"):
        html = render_template("structural_segment.html", segment=segment)

    assert "2 detected rows" in html
    assert "2 detected columns" in html
    assert "Running" in html
    assert "Parts move freely" in html
    assert "Coordinate-derived reading order" in html
    assert "Raw extracted source chunks" in html
    assert '<details class="raw-chunks">' in html
    assert '<details class="raw-chunks" open>' not in html


def test_semantic_context_template_renders_continued_table_series():
    segment = {
        "document": {"doc_id": "doc_001", "title": "Handbook"},
        "context_mode": "semantic_unit",
        "matched_entry_index": 2,
        "semantic_unit": {
            "retrieval_chunk_count": 1,
            "char_count": 100,
        },
        "table_layout": {"layout_id": "page_0659_table_01"},
        "table_layouts": [
            {
                "caption": "Table 4. Preferred Shaft Basis Fits",
                "page_number": 658,
                "row_count": 2,
                "column_count": 1,
                "cells": [{}],
                "grid": [["First-page data"]],
                "reading_order_text": "First-page data",
            },
            {
                "caption": "Table 4. (Continued) Preferred Shaft Basis Fits",
                "page_number": 659,
                "row_count": 2,
                "column_count": 1,
                "cells": [{}],
                "grid": [["Continued data"]],
                "reading_order_text": "Continued data",
            },
        ],
        "context_entries": [],
        "previous": None,
        "current": None,
        "next": None,
    }

    with app.test_request_context("/"):
        html = render_template("structural_segment.html", segment=segment)

    normalized_html = " ".join(html.split())
    assert "Continued table series" in html
    assert "2 PDF pages" in normalized_html
    assert "Pages 658–659" in normalized_html
    assert "First-page data" in html
    assert "Continued data" in html
