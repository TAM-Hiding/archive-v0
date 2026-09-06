import json

from ingestion.chunkers import (
    build_chunks,
    build_toc_hierarchy_lookup,
    infer_printed_page_offset,
    is_likely_heading,
    normalize_heading,
    parse_cleaned_text_into_pages,
    resolve_toc_hierarchy,
    save_chunks,
    split_oversized_block,
    split_page_into_blocks,
    split_text_into_paragraphs,
    split_text_into_sentence_groups,
)


def test_normalize_heading():
    result = normalize_heading("  Materials   and Methods  ")

    assert result == "materials and methods"


def test_known_heading_is_detected():
    assert is_likely_heading("Introduction") is True
    assert is_likely_heading("RESULTS") is True


def test_normal_sentence_is_not_heading():
    assert is_likely_heading("This is a normal sentence.") is False


def test_long_text_is_not_heading():
    text = "A" * 81

    assert is_likely_heading(text) is False


def test_parse_cleaned_text_into_pages():
    cleaned_text = (
        "--- PAGE 1 ---\n"
        "First page text.\n"
        "\n"
        "--- PAGE 2 ---\n"
        "Second page text."
    )

    result = parse_cleaned_text_into_pages(cleaned_text)

    assert result == [
        {
            "page_number": 1,
            "text": "First page text.",
        },
        {
            "page_number": 2,
            "text": "Second page text.",
        },
    ]


def test_text_before_first_page_marker_is_ignored():
    cleaned_text = (
        "Unmarked preamble\n"
        "--- PAGE 1 ---\n"
        "Marked content."
    )

    result = parse_cleaned_text_into_pages(cleaned_text)

    assert result == [
        {
            "page_number": 1,
            "text": "Marked content.",
        }
    ]


def test_split_page_into_heading_blocks():
    page_text = (
        "INTRODUCTION\n"
        "This is the introduction.\n"
        "\n"
        "RESULTS\n"
        "These are the results."
    )

    result, final_heading, final_subheading = split_page_into_blocks(3, page_text)

    assert result == [
        {
            "page_number": 3,
            "heading": "INTRODUCTION",
            "subheading": None,
            "running_header": None,
            "text": "This is the introduction.",
        },
        {
            "page_number": 3,
            "heading": "RESULTS",
            "subheading": None,
            "running_header": None,
            "text": "These are the results.",
        },
    ]

    assert final_heading == "RESULTS"

def test_inline_abstract_heading():
    page_text = "Abstract: This paper describes a deterministic archive."

    result, final_heading, final_subheading = split_page_into_blocks(1, page_text)

    assert result == [
        {
            "page_number": 1,
            "heading": "Abstract",
            "subheading": None,
            "running_header": None,
            "text": "This paper describes a deterministic archive.",
        }
    ]

    assert final_heading == "Abstract"

def test_heading_state_persists_across_pages():
    toc_candidates = {
        "logarithms",
        "imaginary and complex numbers",
    }

    page_26 = (
        "14 LOGARITHMS\n"
        "Logarithms\n"
        "Logarithms have long been used..."
    )

    page_27 = (
        "COMPLEX NUMBERS 15\n"
        "Continuation of logarithms text.\n"
        "Imaginary and Complex Numbers\n"
        "Complex Numbers.-Complex numbers represent..."
    )

    blocks_26, final_heading, final_subheading = split_page_into_blocks(
        26,
        page_26,
        toc_heading_candidates=toc_candidates,
    )

    blocks_27, final_heading, final_subheading = split_page_into_blocks(
        27,
        page_27,
        inherited_heading=final_heading,
        toc_heading_candidates=toc_candidates,
    )

    assert blocks_26[0]["heading"] == "Logarithms"

    assert blocks_27[0]["heading"] == "Logarithms"
    assert blocks_27[0]["running_header"] == "COMPLEX NUMBERS 15"

    assert blocks_27[1]["heading"] == "Imaginary and Complex Numbers"
    assert final_heading == "Imaginary and Complex Numbers"
    
def test_non_toc_title_case_line_is_not_promoted_to_heading():
    toc_candidates = {"logarithms"}

    page_text = (
        "14 LOGARITHMS\n"
        "Constants Involving π Frequently Used in Mathematical Calculations\n"
        "Some table data here.\n"
        "Logarithms\n"
        "Actual logarithms body."
    )

    blocks, final_heading, final_subheading = split_page_into_blocks(
        26,
        page_text,
        inherited_heading="Powers and Roots",
        toc_heading_candidates=toc_candidates,
    )

    assert blocks[0]["heading"] == "Powers and Roots"
    assert (
        "Constants Involving π Frequently Used in Mathematical Calculations"
        in blocks[0]["text"]
    )

    assert blocks[1]["heading"] == "Logarithms"
    assert final_heading == "Logarithms"


def test_exact_inline_toc_heading_is_promoted_to_peer_section():
    blocks, final_heading, final_subheading = split_page_into_blocks(
        29,
        "Permutations.-Body text about permutations.",
        inherited_heading="Factorial",
        inherited_subheading="Factorial Notation",
        toc_heading_candidates={"factorial", "permutations"},
        toc_heading_lookup={
            "factorial": "Factorial",
            "permutations": "Permutations",
        },
    )

    assert blocks == [
        {
            "page_number": 29,
            "heading": "Permutations",
            "subheading": None,
            "running_header": None,
            "text": "Body text about permutations.",
        }
    ]
    assert final_heading == "Permutations"
    assert final_subheading is None


def test_expanded_inline_toc_heading_preserves_subheading():
    blocks, final_heading, final_subheading = split_page_into_blocks(
        29,
        "Factorial Notation.-Body text about factorials.",
        inherited_heading="Imaginary and Complex Numbers",
        inherited_subheading="Operations on Complex Numbers",
        toc_heading_candidates={"factorial"},
        toc_heading_lookup={"factorial": "Factorial"},
    )

    assert blocks == [
        {
            "page_number": 29,
            "heading": "Factorial",
            "subheading": "Factorial Notation",
            "running_header": None,
            "text": "Body text about factorials.",
        }
    ]
    assert final_heading == "Factorial"
    assert final_subheading == "Factorial Notation"


def test_expanded_standalone_toc_heading_preserves_subheading():
    blocks, final_heading, final_subheading = split_page_into_blocks(
        29,
        (
            "Prime Numbers and Factors of Numbers\n"
            "Body text about prime numbers and factors."
        ),
        inherited_heading="Combinations",
        toc_heading_candidates={"prime numbers and factors"},
        toc_heading_lookup={
            "prime numbers and factors": "Prime Numbers and Factors",
        },
    )

    assert blocks == [
        {
            "page_number": 29,
            "heading": "Prime Numbers and Factors",
            "subheading": "Prime Numbers and Factors of Numbers",
            "running_header": None,
            "text": "Body text about prime numbers and factors.",
        }
    ]
    assert final_heading == "Prime Numbers and Factors"
    assert final_subheading == "Prime Numbers and Factors of Numbers"


def test_inline_subheading_state_persists_across_pages():
    toc_candidates = {"imaginary and complex numbers"}
    toc_lookup = {
        "imaginary and complex numbers": "Imaginary and Complex Numbers",
    }

    blocks_28, final_heading, final_subheading = split_page_into_blocks(
        28,
        "Operations on Complex Numbers.-Body starts on this page.",
        inherited_heading="Imaginary and Complex Numbers",
        toc_heading_candidates=toc_candidates,
        toc_heading_lookup=toc_lookup,
    )

    blocks_29, final_heading, final_subheading = split_page_into_blocks(
        29,
        "Continued body on the next page.",
        inherited_heading=final_heading,
        inherited_subheading=final_subheading,
        toc_heading_candidates=toc_candidates,
        toc_heading_lookup=toc_lookup,
    )

    assert blocks_28[0]["heading"] == "Imaginary and Complex Numbers"
    assert blocks_28[0]["subheading"] == "Operations on Complex Numbers"
    assert blocks_29 == [
        {
            "page_number": 29,
            "heading": "Imaginary and Complex Numbers",
            "subheading": "Operations on Complex Numbers",
            "running_header": None,
            "text": "Continued body on the next page.",
        }
    ]
    assert final_heading == "Imaginary and Complex Numbers"
    assert final_subheading == "Operations on Complex Numbers"

def test_split_text_into_paragraphs():
    text = "First paragraph.\n\nSecond paragraph.\n\n\nThird paragraph."

    result = split_text_into_paragraphs(text)

    assert result == [
        "First paragraph.",
        "Second paragraph.",
        "Third paragraph.",
    ]


def test_split_text_into_sentence_groups():
    text = (
        "First sentence. "
        "Second sentence is longer. "
        "Third sentence finishes the example."
    )

    result = split_text_into_sentence_groups(text, target_chars=35)

    assert result == [
        "First sentence.",
        "Second sentence is longer.",
        "Third sentence finishes the example.",
    ]


def test_oversized_block_splits_at_paragraph_boundaries():
    block = {
        "page_number": 4,
        "heading": "Discussion",
        "text": (
            "Paragraph one contains useful information.\n\n"
            "Paragraph two contains different information.\n\n"
            "Paragraph three contains the final information."
        ),
    }

    result = split_oversized_block(block, max_chars=60)

    assert len(result) == 3
    assert all(chunk["page_number"] == 4 for chunk in result)
    assert all(chunk["heading"] == "Discussion" for chunk in result)
    assert result[0]["text"].startswith("Paragraph one")
    assert result[1]["text"].startswith("Paragraph two")
    assert result[2]["text"].startswith("Paragraph three")


def test_small_block_is_returned_unchanged():
    block = {
        "page_number": 2,
        "heading": None,
        "text": "A short block.",
    }

    result = split_oversized_block(block, max_chars=1200)

    assert result == [block]


def test_build_chunks_creates_expected_metadata():
    cleaned_text = (
        "--- PAGE 1 ---\n"
        "INTRODUCTION\n"
        "Archive stores deterministic document chunks.\n"
        "\n"
        "--- PAGE 2 ---\n"
        "RESULTS\n"
        "The chunks retain page and heading metadata."
    )

    result = build_chunks("document_123", cleaned_text)

    assert len(result) == 2

    first_chunk = result[0]
    second_chunk = result[1]

    assert first_chunk["chunk_id"] == "document_123_chunk_0001"
    assert first_chunk["doc_id"] == "document_123"
    assert first_chunk["chunk_index"] == 1
    assert first_chunk["page_start"] == 1
    assert first_chunk["page_end"] == 1
    assert first_chunk["section_heading"] == "INTRODUCTION"
    assert first_chunk["char_count"] == len(first_chunk["text"])
    assert first_chunk["char_start"] == 0
    assert first_chunk["char_end"] == len(first_chunk["text"])

    assert second_chunk["chunk_id"] == "document_123_chunk_0002"
    assert second_chunk["chunk_index"] == 2
    assert second_chunk["page_start"] == 2
    assert second_chunk["section_heading"] == "RESULTS"
    assert second_chunk["char_start"] == first_chunk["char_end"]


def test_build_chunks_returns_empty_list_without_page_markers():
    result = build_chunks(
        "document_123",
        "This text has no page markers.",
    )

    assert result == []


def test_save_chunks(tmp_path):
    chunks = [
        {
            "chunk_id": "document_123_chunk_0001",
            "doc_id": "document_123",
            "chunk_index": 1,
            "page_start": 1,
            "page_end": 1,
            "section_heading": "Introduction",
            "text": "Stored text.",
            "char_count": 12,
            "char_start": 0,
            "char_end": 12,
        }
    ]

    output_path = tmp_path / "nested" / "chunks.json"

    result = save_chunks(output_path, chunks)

    assert result == output_path
    assert output_path.exists()

    saved_data = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved_data == chunks

def test_oversized_paragraph_inside_multi_paragraph_block_is_split():
    text = (
        "Short opening paragraph.\n\n"
        + ("This is an intentionally oversized sentence for testing. " * 100)
        + "\n\nShort closing paragraph."
    )

    block = {
        "page_number": 1,
        "heading": "Test Section",
        "text": text,
    }

    max_chars = 500

    chunks = split_oversized_block(
        block,
        max_chars=max_chars,
    )

    assert len(chunks) > 1
    assert all(len(chunk["text"]) <= max_chars for chunk in chunks)


def test_toc_hierarchy_lookup_preserves_duplicate_title_candidates():
    entries = [
        {
            "title": "Introduction",
            "major_section": "MACHINING OPERATIONS",
            "category": "MICROMACHINING",
            "printed_page": 1128,
        },
        {
            "title": "Introduction",
            "major_section": "MACHINE ELEMENTS",
            "category": "FLUID POWER",
            "printed_page": 2667,
        },
    ]

    lookup = build_toc_hierarchy_lookup(entries)

    assert [item["printed_page"] for item in lookup["introduction"]] == [
        1128,
        2667,
    ]


def test_infer_printed_page_offset_uses_exact_unambiguous_headings():
    pages = [
        {"page_number": 22, "text": "Alpha"},
        {"page_number": 32, "text": "Beta"},
        {"page_number": 42, "text": "Gamma"},
    ]
    entries = [
        {"title": "Alpha", "printed_page": 10},
        {"title": "Beta", "printed_page": 20},
        {"title": "Gamma", "printed_page": 30},
    ]

    assert infer_printed_page_offset(pages, entries) == 12


def test_infer_printed_page_offset_rejects_tied_evidence():
    pages = [
        {"page_number": 11, "text": "Alpha"},
        {"page_number": 21, "text": "Beta"},
        {"page_number": 31, "text": "Gamma"},
        {"page_number": 52, "text": "Delta"},
        {"page_number": 62, "text": "Epsilon"},
        {"page_number": 72, "text": "Zeta"},
    ]
    entries = [
        {"title": "Alpha", "printed_page": 10},
        {"title": "Beta", "printed_page": 20},
        {"title": "Gamma", "printed_page": 30},
        {"title": "Delta", "printed_page": 50},
        {"title": "Epsilon", "printed_page": 60},
        {"title": "Zeta", "printed_page": 70},
    ]

    assert infer_printed_page_offset(pages, entries) is None


def test_ambiguous_toc_hierarchy_resolves_by_document_position():
    lookup = build_toc_hierarchy_lookup(
        [
            {
                "title": "Introduction",
                "major_section": "MACHINING OPERATIONS",
                "category": "MICROMACHINING",
                "printed_page": 1128,
            },
            {
                "title": "Introduction",
                "major_section": "MACHINE ELEMENTS",
                "category": "FLUID POWER",
                "printed_page": 2667,
            },
        ]
    )

    result = resolve_toc_hierarchy(
        "Introduction",
        physical_page=2679,
        hierarchy_lookup=lookup,
        printed_page_offset=12,
    )

    assert result["major_section"] == "MACHINE ELEMENTS"
    assert result["category"] == "FLUID POWER"
    assert result["printed_page"] == 2667


def test_ambiguous_toc_hierarchy_remains_unset_without_page_alignment():
    lookup = build_toc_hierarchy_lookup(
        [
            {"title": "Definitions", "printed_page": 623},
            {"title": "Definitions", "printed_page": 1436},
        ]
    )

    assert resolve_toc_hierarchy(
        "Definitions",
        physical_page=1448,
        hierarchy_lookup=lookup,
        printed_page_offset=None,
    ) == {}
