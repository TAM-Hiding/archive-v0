from ingestion.figure_links import link_figure_layouts_to_entries


def test_link_figure_layouts_uses_caption_bearing_entry():
    cleaned = "Earlier chunk.\nFig. 1. Design features of a micrometer."
    entries = [
        {
            "entry_index": 1,
            "page_start": 754,
            "source_char_start": 0,
            "source_char_end": 14,
        },
        {
            "entry_index": 2,
            "page_start": 754,
            "source_char_start": 15,
            "source_char_end": len(cleaned),
        },
    ]
    layouts = [{
        "layout_id": "page_0754_figure_01",
        "page_number": 754,
        "caption": "Fig. 1. Design features of a micrometer",
        "caption_key": "fig 1 design features of a micrometer",
        "label_text": "Anvil Spindle Frame",
    }]

    linked = link_figure_layouts_to_entries(entries, layouts, cleaned)

    assert linked == 1
    assert "figure_layout_ids" not in entries[0]
    assert entries[1]["figure_layout_ids"] == ["page_0754_figure_01"]
    assert entries[1]["figure_search_text"] == "Anvil Spindle Frame"
