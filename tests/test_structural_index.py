from ingestion.structural_index import build_structural_index


def test_build_structural_index_preserves_hierarchy_metadata():
    chunks = [
        {
            "chunk_index": 7,
            "semantic_unit_id": "doc_001_unit_0003",
            "semantic_unit_index": 3,
            "semantic_unit_page_start": 27,
            "semantic_unit_page_end": 30,
            "semantic_unit_char_count": 2400,
            "semantic_unit_block_count": 4,
            "retrieval_chunk_index": 2,
            "retrieval_chunk_count": 4,
            "page_start": 28,
            "page_end": 29,
            "section_heading": "Imaginary and Complex Numbers",
            "subheading": "Operations on Complex Numbers",
            "content_type": "prose",
            "table_caption": None,
            "major_section": "MATHEMATICS",
            "category": "NUMBERS, FRACTIONS, AND DECIMALS",
            "printed_page": 15,
            "section_printed_page": 15,
            "estimated_printed_page": 16,
            "printed_page_offset": 12,
            "running_header": "FACTORIAL 17",
            "char_count": 34,
            "char_start": 120,
            "char_end": 154,
            "source_char_start": 220,
            "source_char_end": 254,
            "text": "Continued complex-number operations.",
        }
    ]

    result = build_structural_index(chunks)

    assert result == [
        {
            "entry_index": 0,
            "chunk_index": 7,
            "semantic_unit_id": "doc_001_unit_0003",
            "semantic_unit_index": 3,
            "semantic_unit_page_start": 27,
            "semantic_unit_page_end": 30,
            "semantic_unit_char_count": 2400,
            "semantic_unit_block_count": 4,
            "retrieval_chunk_index": 2,
            "retrieval_chunk_count": 4,
            "page_start": 28,
            "page_end": 29,
            "section_heading": "Imaginary and Complex Numbers",
            "subheading": "Operations on Complex Numbers",
            "content_type": "prose",
            "table_caption": "",
            "major_section": "MATHEMATICS",
            "category": "NUMBERS, FRACTIONS, AND DECIMALS",
            "printed_page": 15,
            "section_printed_page": 15,
            "estimated_printed_page": 16,
            "printed_page_offset": 12,
            "running_header": "FACTORIAL 17",
            "layout_hint": "",
            "char_count": 34,
            "char_start": 120,
            "char_end": 154,
            "source_char_start": 220,
            "source_char_end": 254,
            "preview": "Continued complex-number operations.",
            "search_text": "",
        }
    ]


def test_build_structural_index_uses_empty_subheading_when_missing():
    result = build_structural_index(
        [
            {
                "chunk_index": 1,
                "text": "Section body.",
            }
        ]
    )

    assert result[0]["subheading"] == ""


def test_build_structural_index_preserves_equation_layout_hint():
    result = build_structural_index([{
        "chunk_index": 1,
        "text": "x = --------\n    4",
        "layout_hint": "equation",
    }])

    assert result[0]["layout_hint"] == "equation"


def test_structural_index_supports_legacy_printed_page_metadata():
    result = build_structural_index(
        [
            {
                "chunk_index": 1,
                "printed_page": 15,
                "text": "Legacy chunk body.",
            }
        ]
    )

    assert result[0]["printed_page"] == 15
    assert result[0]["section_printed_page"] == 15
    assert result[0]["estimated_printed_page"] is None
    assert result[0]["printed_page_offset"] is None
