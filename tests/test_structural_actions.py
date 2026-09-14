from flask import render_template

import archive
from app import app


def test_structure_index_renders_heading_hierarchy_before_entry_locator():
    document = {
        "document": {
            "doc_id": "doc_001",
            "title": "Machinery's Handbook",
        },
        "entries": [{
            "entry_index": 25,
            "chunk_index": 26,
            "page_start": 10,
            "page_end": 10,
            "char_count": 204,
            "section_heading": "Table of Contents",
            "subheading": "DIMENSIONING, GAGING, AND MEASURING",
            "preview": "Drafting practices and dimensional data.",
        }],
    }

    with app.test_request_context("/"):
        html = render_template("structural_index.html", document=document)

    normalized_html = " ".join(html.split())

    assert "<span>Table of Contents</span>" in normalized_html
    assert '<span class="hierarchy-separator">›</span>' in normalized_html
    assert "<span>DIMENSIONING, GAGING, AND MEASURING</span>" in normalized_html
    assert '<span class="entry-locator">Entry 25</span>' in normalized_html
    assert normalized_html.index("Table of Contents") < normalized_html.index("Entry 25")


def test_structure_index_collapses_contents_and_front_matter_groups():
    entries = [
        {
            "entry_index": 1,
            "chunk_index": 2,
            "page_start": 9,
            "page_end": 9,
            "char_count": 100,
            "section_heading": "Acknowledgments",
            "subheading": "",
            "content_type": "prose",
            "preview": "Thanks to the contributors.",
        },
        {
            "entry_index": 2,
            "chunk_index": 3,
            "page_start": 10,
            "page_end": 10,
            "char_count": 200,
            "section_heading": "Table of Contents",
            "subheading": "MACHINING OPERATIONS",
            "content_type": "contents",
            "preview": "Cutting speeds and feeds.",
        },
        {
            "entry_index": 3,
            "chunk_index": 4,
            "page_start": 11,
            "page_end": 11,
            "char_count": 180,
            "section_heading": "Table of Contents",
            "subheading": "FASTENERS",
            "content_type": "contents",
            "preview": "Threaded fasteners.",
        },
        {
            "entry_index": 4,
            "chunk_index": 5,
            "page_start": 17,
            "page_end": 17,
            "char_count": 300,
            "section_heading": "Ratio and Proportion",
            "subheading": "",
            "content_type": "prose",
            "preview": "Ratios compare two quantities.",
        },
    ]
    document = {
        "document": {"doc_id": "doc_001", "title": "Handbook"},
        "entries": entries,
        "display_items": archive.build_structural_display_items(entries),
    }

    with app.test_request_context("/"):
        html = render_template("structural_index.html", document=document)

    assert html.count('<details class="structure-group">') == 2
    assert "Acknowledgments" in html
    assert "Table of Contents" in html
    assert "2 entries · Pages 10–11" in " ".join(html.split())
    assert "Ratio and Proportion" in html


def test_structure_index_carries_front_matter_labels_through_fragments():
    entries = [
        {
            "entry_index": 0,
            "page_start": 3,
            "page_end": 3,
            "section_heading": "A REFERENCE BOOK",
            "content_type": "prose",
            "preview": "Title-page copy.",
        },
        {
            "entry_index": 1,
            "page_start": 5,
            "page_end": 5,
            "section_heading": "Copyright",
            "content_type": "prose",
            "preview": "Copyright notice.",
        },
        {
            "entry_index": 2,
            "page_start": 5,
            "page_end": 5,
            "section_heading": "30TH EDITION",
            "content_type": "prose",
            "preview": "First printing.",
        },
        {
            "entry_index": 3,
            "page_start": 8,
            "page_end": 9,
            "section_heading": "Acknowledgments",
            "content_type": "prose",
            "preview": "Named contributors.",
        },
        {
            "entry_index": 4,
            "page_start": 9,
            "page_end": 9,
            "section_heading": "MANUFACTURING DATA on page 123",
            "content_type": "prose",
            "preview": "Acknowledgment continuation.",
        },
        {
            "entry_index": 5,
            "page_start": 10,
            "page_end": 10,
            "section_heading": "Table of Contents",
            "content_type": "contents",
            "preview": "Main divisions.",
        },
        {
            "entry_index": 6,
            "page_start": 15,
            "page_end": 15,
            "section_heading": "NUMBERS, FRACTIONS, AND DECIMALS",
            "content_type": "prose",
            "preview": "Body content.",
        },
    ]

    items = archive.build_structural_display_items(entries)

    assert [item.get("label") for item in items[:-1]] == [
        "Publication Details",
        "Copyright",
        "Acknowledgments",
        "Table of Contents",
    ]
    assert items[1]["entry_count"] == 2
    assert items[2]["entry_count"] == 2
    assert items[-1]["kind"] == "entry"


def test_later_section_contents_do_not_extend_the_front_matter_zone():
    entries = [
        {
            "entry_index": 0,
            "page_start": 3,
            "page_end": 3,
            "section_heading": "Title Page",
            "content_type": "prose",
        },
        {
            "entry_index": 1,
            "page_start": 10,
            "page_end": 10,
            "section_heading": "Table of Contents",
            "content_type": "contents",
        },
        {
            "entry_index": 2,
            "page_start": 15,
            "page_end": 15,
            "section_heading": "MATHEMATICS",
            "content_type": "prose",
        },
        {
            "entry_index": 3,
            "page_start": 16,
            "page_end": 16,
            "section_heading": "Section Contents",
            "content_type": "contents",
        },
    ]

    items = archive.build_structural_display_items(entries)

    assert [item.get("label") for item in items] == [
        "Title Page",
        "Table of Contents",
        None,
        "Table of Contents",
    ]
    assert items[2]["kind"] == "entry"


def test_structure_index_coalesces_retrieval_chunks_for_one_table():
    entries = [
        {
            "entry_index": 41,
            "chunk_index": 42,
            "semantic_unit_id": "doc_001_unit_0041",
            "retrieval_chunk_index": 1,
            "retrieval_chunk_count": 2,
            "page_start": 15,
            "page_end": 15,
            "char_count": 1174,
            "section_heading": "NUMBERS, FRACTIONS, AND DECIMALS",
            "content_type": "table",
            "table_caption": "Table 1. Fractional and Decimal Inch",
            "preview": "First half of flattened table.",
        },
        {
            "entry_index": 42,
            "chunk_index": 43,
            "semantic_unit_id": "doc_001_unit_0041",
            "retrieval_chunk_index": 2,
            "retrieval_chunk_count": 2,
            "page_start": 15,
            "page_end": 15,
            "char_count": 1141,
            "section_heading": "NUMBERS, FRACTIONS, AND DECIMALS",
            "content_type": "table",
            "table_caption": "Table 1. Fractional and Decimal Inch",
            "preview": "Second half of flattened table.",
        },
    ]
    document = {
        "document": {"doc_id": "doc_001", "title": "Handbook"},
        "entries": entries,
        "display_items": archive.build_structural_display_items(entries),
    }

    with app.test_request_context("/"):
        html = render_template("structural_index.html", document=document)

    assert html.count('class="artifact-preview artifact-table"') == 1
    assert "2 retrieval chunks" in " ".join(html.split())
    assert "2315 chars" in " ".join(html.split())


def test_structure_index_uses_artifact_cards_for_tables_and_figures():
    document = {
        "document": {"doc_id": "doc_001", "title": "Handbook"},
        "entries": [
            {
                "entry_index": 7,
                "chunk_index": 8,
                "page_start": 654,
                "page_end": 654,
                "char_count": 900,
                "section_heading": "Preferred Fits",
                "subheading": "",
                "content_type": "table",
                "table_caption": "Table 2. Metric Clearance Fits",
                "preview": "Basic Size Loose Running Free Running",
            },
            {
                "entry_index": 8,
                "chunk_index": 9,
                "page_start": 754,
                "page_end": 754,
                "char_count": 700,
                "section_heading": "Caliper Micrometer",
                "subheading": "",
                "content_type": "prose",
                "figure_layout_ids": ["page_0754_figure_01"],
                "preview": "Anvil spindle thimble barrel",
            },
        ],
    }

    with app.test_request_context("/"):
        html = render_template("structural_index.html", document=document)

    assert 'class="artifact-preview artifact-table"' in html
    assert "Table 2. Metric Clearance Fits" in html
    assert "Open table" in html
    assert 'class="artifact-preview artifact-figure"' in html
    assert "1 recovered" in html
    assert "Open figure" in html
    assert "Show extracted text preview" not in html
    assert "Basic Size Loose Running Free Running" not in html
    assert "Anvil spindle thimble barrel" not in html


def test_search_result_replaces_flattened_table_preview_with_artifact_card():
    note = {
        "id": "structural:doc_001:7",
        "title": "Table 2. Metric Clearance Fits",
        "tags": [],
        "tags_display": "—",
        "aliases": [],
        "category": "reference > machining",
        "is_generated": True,
        "meta": {
            "structural_hit": True,
            "source_doc_id": "doc_001",
            "entry_index": 7,
            "content_type": "table",
            "table_caption": "Table 2. Metric Clearance Fits",
            "figure_layout_ids": [],
            "page_start": 654,
            "page_end": 654,
        },
    }

    with app.test_request_context("/"):
        html = render_template(
            "index.html",
            query="clearance",
            scope="reference",
            results=[(5, note, "Basic Size Loose Running Free Running")],
            expanded_terms=["clearance"],
            message="",
        )

    assert 'class="artifact-preview artifact-table"' in html
    assert "Open table" in html
    assert "Show matched extracted text" not in html
    assert "Basic Size Loose Running Free Running" not in html


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
    assert 'class="button-secondary button-compact">Context' in html
    assert 'class="button-secondary button-compact">Source' in html
    assert ">[Context]<" not in html
    assert ">[Source]<" not in html
    assert ">[Edit]<" not in html
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
            "body": "Anvil Spindle Fig. 1. Micrometer Micrometer discussion.",
            "display_body": "Micrometer discussion.",
            "figure_labels": ["Anvil\nSpindle\nFig. 1. Micrometer"],
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
    assert "Extracted figure labels" in html
    assert "Micrometer discussion." in html


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
