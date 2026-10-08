from copy import deepcopy

from flask import render_template
import pytest

import archive
from app import app
from ingestion.chunkers import build_chunks
from ingestion.table_captions import is_table_caption, named_table_caption
from ingestion.table_layout import extract_caption_above_table


@pytest.mark.parametrize("caption", [
    "Prime Number and Factor Table for 1 to 1199",
    "Prime Number and Factor Table for 8401 to 9599",
    "Prime Numbers from 9551 to 18691",
    "Conversion Table for 1 to 100",
])
def test_named_captions_and_legacy_flattened_text(caption):
    assert is_table_caption(caption)
    assert named_table_caption(caption + " From 0 100 200 To 100 200 300 1 P P 3") == caption


@pytest.mark.parametrize("text", [
    "Use the factor table for numbers from 1 to 1199.",
    "Prime Numbers and Factors of Numbers",
    "A table for this calculation is shown below.",
])
def test_prose_and_section_heading_are_not_table_captions(text):
    assert not is_table_caption(text)
    assert named_table_caption(text) is None


def test_new_chunks_keep_distinct_named_tables_and_source_lines():
    first = "Prime Number and Factor Table for 1 to 1199"
    second = "Prime Number and Factor Table for 1201 to 2399"
    chunks = build_chunks("doc", f"--- PAGE 31 ---\n{first}\nFrom 0 100 200\n"
                          f"To 100 200 300\n1 P P 3\n3 P P 7\n"
                          f"--- PAGE 32 ---\n{second}\nFrom 1200 1300 1400\n1 P P 3")
    tables = [chunk for chunk in chunks if chunk["content_type"] == "table"]
    assert [chunk["table_caption"] for chunk in tables] == [first, second]
    assert tables[0]["semantic_unit_id"] != tables[1]["semantic_unit_id"]
    assert "\nFrom 0 100 200\nTo 100 200 300\n1 P P 3" in tables[0]["text"]


def test_existing_flattened_tables_get_original_pages_without_rebuilding(monkeypatch):
    entries = []
    for i, page in enumerate(range(31, 40)):
        caption = (f"Prime Number and Factor Table for {i * 1200 + 1} to {(i + 1) * 1200 - 1}"
                   if page < 39 else "Prime Numbers from 9551 to 18691")
        entries.append({"page_start": page, "page_end": page,
                        "preview": caption + " From 0 100 200 To 100 200 300 1 P P 3",
                        "semantic_unit_id": "old-unit", "chunk_index": i,
                        "content_type": "prose"})
    original_entries = deepcopy(entries)
    monkeypatch.setattr(archive, "get_structural_index_for_document", lambda _: {
        "document": {"doc_id": "doc", "title": "Handbook"}, "entries": entries})
    segment = archive.get_structural_segment("doc", 8)
    assert 39 in segment["source_verification_pages"]
    assert len(segment["source_verification_pages"]) <= 8
    assert segment["source_verification_open"]
    assert all(item["unrecovered_table_caption"] for item in segment["context_entries"])
    assert entries == original_entries
    with app.test_request_context("/"):
        html = render_template("structural_segment.html", segment=segment)
    assert 'id="source-page-39"' in html
    assert 'href="#source-page-39"' in html
    assert "Raw table text" in html
    assert "columns have not been recovered" in html


def test_known_table_without_geometry_gets_source_preview():
    pages = archive.source_verification_pages([], [{
        "entry": {"content_type": "table", "page_start": 11, "page_end": 12}}])
    assert pages == [11, 12]


def test_named_caption_is_recognized_above_geometry():
    caption = "Prime Number and Factor Table for 1 to 1199"

    class Page:
        def crop(self, bbox):
            return self

        def extract_text(self, **kwargs):
            return "PRIME NUMBERS\n" + caption

    assert extract_caption_above_table(Page(), [0, 100, 500, 700]) == caption
