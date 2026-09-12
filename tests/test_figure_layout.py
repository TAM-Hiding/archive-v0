from ingestion.figure_layout import (
    extract_page_figure_layouts,
    find_figure_candidate_pages,
    parse_page_spec,
)


class FakeCrop:
    def extract_text(self, **kwargs):
        return "Anvil Spindle Frame\nFig. 1. Micrometer"


class FakePage:
    bbox = (0, 0, 612, 792)
    images = []
    rects = []
    curves = []
    lines = [
        {
            "object_type": "line",
            "x0": 130,
            "top": 80,
            "x1": 480,
            "bottom": 190,
        }
    ]

    def extract_words(self, **kwargs):
        return [
            {
                "text": "Anvil",
                "x0": 140,
                "x1": 175,
                "top": 90,
                "bottom": 100,
            },
            {
                "text": "Fig.",
                "x0": 210,
                "x1": 230,
                "top": 200,
                "bottom": 210,
            },
            {
                "text": "1.",
                "x0": 232,
                "x1": 240,
                "top": 200,
                "bottom": 210,
            },
            {
                "text": "Micrometer",
                "x0": 242,
                "x1": 300,
                "top": 200,
                "bottom": 210,
            },
        ]

    def crop(self, bbox):
        return FakeCrop()


def test_extract_page_figure_layouts_finds_vector_figure_above_caption():
    layouts = extract_page_figure_layouts(FakePage(), 754)

    assert len(layouts) == 1
    assert layouts[0]["layout_id"] == "page_0754_figure_01"
    assert layouts[0]["caption"] == "Fig. 1. Micrometer"
    assert layouts[0]["vector_object_count"] == 1
    assert layouts[0]["embedded_image_count"] == 0
    assert "Anvil" in layouts[0]["label_text"]


def test_find_figure_candidate_pages_requires_caption_at_line_start():
    cleaned = (
        "--- PAGE 1 ---\nSee Fig. 1 for details.\n"
        "--- PAGE 2 ---\nFig. 2. Actual caption\n"
    )

    assert find_figure_candidate_pages(cleaned) == {2}


def test_parse_page_spec_supports_lists_and_ranges():
    assert parse_page_spec("754,760-762") == {754, 760, 761, 762}
