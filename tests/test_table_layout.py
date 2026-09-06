from ingestion.table_layout import (
    discard_nested_tables,
    group_words_into_positioned_lines,
    match_layout_to_caption,
    normalize_table_caption,
    write_sharded_table_layout_store,
)


class FakeTable:
    def __init__(self, bbox):
        self.bbox = bbox


def test_discard_nested_tables_keeps_outer_and_independent_tables():
    outer = FakeTable((10, 10, 100, 100))
    nested = FakeTable((20, 20, 40, 40))
    independent = FakeTable((110, 10, 180, 80))

    assert discard_nested_tables([outer, nested, independent]) == [
        outer,
        independent,
    ]


def test_group_words_into_positioned_lines_uses_geometry_not_input_order():
    words = [
        {"text": "20", "x0": 80, "x1": 90, "top": 30, "bottom": 38},
        {"text": "Width", "x0": 50, "x1": 75, "top": 10, "bottom": 18},
        {"text": "10", "x0": 50, "x1": 60, "top": 30.8, "bottom": 38.8},
    ]

    result = group_words_into_positioned_lines(words, y_tolerance=1)

    assert [line["text"] for line in result] == ["Width", "10 20"]
    assert result[1]["tokens"] == [[50.0, 60.0, "10"], [80.0, 90.0, "20"]]


def test_match_layout_to_caption_normalizes_punctuation_and_case():
    layouts = [{
        "layout_id": "page_0002_table_01",
        "page_number": 2,
        "caption_key": normalize_table_caption(
            "Table 6. Keyway Dimensions for Metric Woodruff Keys"
        ),
    }]

    result = match_layout_to_caption(
        layouts,
        2,
        "TABLE 6 — Keyway Dimensions for Metric Woodruff Keys",
    )

    assert result == layouts[0]


def test_match_layout_to_caption_does_not_guess_between_multiple_tables():
    layouts = [
        {"layout_id": "a", "page_number": 2, "caption_key": "table 5 alpha"},
        {"layout_id": "b", "page_number": 2, "caption_key": "table 6 beta"},
    ]

    assert match_layout_to_caption(layouts, 2, "Table 7. Gamma") is None


def test_write_sharded_table_layout_store_creates_compact_manifest(tmp_path):
    layout_path = tmp_path / "table_layout.json"
    payload = {
        "doc_id": "doc_001",
        "source_filename": "handbook.pdf",
        "layouts": [{
            "layout_id": "page_0008_table_01",
            "page_number": 8,
            "table_index": 1,
            "caption": "Table 1. Preferred Fits",
            "bbox": [10, 20, 100, 200],
            "row_count": 4,
            "column_count": 3,
            "grid": [["Fit", "Shaft", "Hole"]],
            "cells": [{"text": "Fit"}],
            "reading_order_text": "Fit Shaft Hole",
        }],
    }

    manifest = write_sharded_table_layout_store(layout_path, payload)

    assert manifest["storage_mode"] == "sharded"
    assert manifest["layout_count"] == 1
    assert "grid" not in manifest["layouts"][0]
    shard_path = tmp_path / manifest["layouts"][0]["file"]
    assert shard_path.is_file()
    assert "Fit Shaft Hole" in shard_path.read_text(encoding="utf-8")
