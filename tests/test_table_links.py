import json

from ingestion.table_links import restore_table_layout_links


def test_restore_table_layout_links_uses_sharded_manifest(tmp_path):
    layout_path = tmp_path / "table_layout.json"
    layout_path.write_text(
        json.dumps({
            "storage_mode": "sharded",
            "layouts": [{
                "layout_id": "page_0008_table_01",
                "page_number": 8,
                "caption": "Table 6. Metric Woodruff Keys",
                "file": "table_layouts/page_0008_table_01.json",
            }],
        }),
        encoding="utf-8",
    )
    entries = [{
        "content_type": "table",
        "page_start": 8,
        "table_caption": "TABLE 6 — Metric Woodruff Keys",
    }]

    linked_count = restore_table_layout_links(
        entries,
        {"table_layout_file": str(layout_path)},
    )

    assert linked_count == 1
    assert entries[0]["table_layout_id"] == "page_0008_table_01"
