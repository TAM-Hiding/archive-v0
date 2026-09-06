from ingestion.structural_index import build_structural_index


def test_build_structural_index_preserves_hierarchy_metadata():
    chunks = [
        {
            "chunk_index": 7,
            "page_start": 28,
            "page_end": 29,
            "section_heading": "Imaginary and Complex Numbers",
            "subheading": "Operations on Complex Numbers",
            "major_section": "MATHEMATICS",
            "category": "NUMBERS, FRACTIONS, AND DECIMALS",
            "printed_page": 15,
            "running_header": "FACTORIAL 17",
            "char_count": 34,
            "char_start": 120,
            "char_end": 154,
            "text": "Continued complex-number operations.",
        }
    ]

    result = build_structural_index(chunks)

    assert result == [
        {
            "entry_index": 0,
            "chunk_index": 7,
            "page_start": 28,
            "page_end": 29,
            "section_heading": "Imaginary and Complex Numbers",
            "subheading": "Operations on Complex Numbers",
            "major_section": "MATHEMATICS",
            "category": "NUMBERS, FRACTIONS, AND DECIMALS",
            "printed_page": 15,
            "running_header": "FACTORIAL 17",
            "char_count": 34,
            "char_start": 120,
            "char_end": 154,
            "preview": "Continued complex-number operations.",
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
