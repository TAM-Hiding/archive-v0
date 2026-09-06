import json

from ingestion.chunkers import (
    apply_front_matter_rules,
    build_chunks,
    build_toc_hierarchy_lookup,
    detect_repeated_page_furniture,
    extract_toc_hierarchy,
    find_source_text_span,
    group_blocks_into_semantic_units,
    infer_printed_page_offset,
    is_likely_heading,
    normalize_heading,
    parse_cleaned_text_into_pages,
    resolve_toc_hierarchy,
    save_chunks,
    split_oversized_block,
    split_page_into_blocks,
    strip_repeated_page_furniture,
    split_text_into_paragraphs,
    split_text_into_sentence_groups,
    toc_heading_candidates_for_page,
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

    assert [page["page_number"] for page in result] == [1, 2]
    assert [page["text"] for page in result] == [
        "First page text.",
        "Second page text.",
    ]
    for page in result:
        assert cleaned_text[
            page["source_char_start"]:page["source_char_end"]
        ] == page["text"]


def test_text_before_first_page_marker_is_ignored():
    cleaned_text = (
        "Unmarked preamble\n"
        "--- PAGE 1 ---\n"
        "Marked content."
    )

    result = parse_cleaned_text_into_pages(cleaned_text)

    assert len(result) == 1
    assert result[0]["page_number"] == 1
    assert result[0]["text"] == "Marked content."
    assert cleaned_text[
        result[0]["source_char_start"]:result[0]["source_char_end"]
    ] == "Marked content."


def test_find_source_text_span_allows_normalized_whitespace():
    source = "Alpha body spans\nmultiple   source lines."

    span = find_source_text_span(
        "Alpha body spans multiple source lines.",
        source,
    )

    assert span is not None
    assert source[slice(*span)] == source


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


def test_front_matter_abstract_promotion_preserves_block_metadata():
    block = {
        "page_number": 1,
        "heading": None,
        "subheading": "Author Summary",
        "running_header": "JOURNAL HEADER 1",
        "source_marker": "native-front-matter",
        "text": "  Abstract: Preserved metadata matters.  ",
    }

    result = apply_front_matter_rules([block])

    assert result == [
        {
            "page_number": 1,
            "heading": "Abstract",
            "subheading": "Author Summary",
            "running_header": "JOURNAL HEADER 1",
            "source_marker": "native-front-matter",
            "text": "Abstract: Preserved metadata matters.",
        }
    ]

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
        "semantic_unit_id": "doc_unit_0007",
        "semantic_unit_index": 7,
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
    assert all(chunk["semantic_unit_id"] == "doc_unit_0007" for chunk in result)
    assert all(chunk["semantic_unit_index"] == 7 for chunk in result)
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
    assert first_chunk["semantic_unit_id"] == "document_123_unit_0001"
    assert first_chunk["semantic_unit_index"] == 1
    assert first_chunk["semantic_unit_page_start"] == 1
    assert first_chunk["semantic_unit_page_end"] == 1
    assert first_chunk["semantic_unit_char_count"] == len(first_chunk["text"])
    assert first_chunk["semantic_unit_block_count"] == 1
    assert first_chunk["retrieval_chunk_index"] == 1
    assert first_chunk["retrieval_chunk_count"] == 1
    assert first_chunk["page_start"] == 1
    assert first_chunk["page_end"] == 1
    assert first_chunk["section_heading"] == "INTRODUCTION"
    assert first_chunk["char_count"] == len(first_chunk["text"])
    assert first_chunk["char_start"] == 0
    assert first_chunk["char_end"] == len(first_chunk["text"])
    assert cleaned_text[
        first_chunk["source_char_start"]:first_chunk["source_char_end"]
    ] == first_chunk["text"]

    assert second_chunk["chunk_id"] == "document_123_chunk_0002"
    assert second_chunk["chunk_index"] == 2
    assert second_chunk["semantic_unit_id"] == "document_123_unit_0002"
    assert second_chunk["semantic_unit_index"] == 2
    assert second_chunk["semantic_unit_page_start"] == 2
    assert second_chunk["semantic_unit_page_end"] == 2
    assert second_chunk["semantic_unit_char_count"] == len(second_chunk["text"])
    assert second_chunk["semantic_unit_block_count"] == 1
    assert second_chunk["retrieval_chunk_index"] == 1
    assert second_chunk["retrieval_chunk_count"] == 1
    assert second_chunk["page_start"] == 2
    assert second_chunk["section_heading"] == "RESULTS"
    assert second_chunk["char_start"] == first_chunk["char_end"]
    assert cleaned_text[
        second_chunk["source_char_start"]:second_chunk["source_char_end"]
    ] == second_chunk["text"]


def test_build_chunks_returns_empty_list_without_page_markers():
    result = build_chunks(
        "document_123",
        "This text has no page markers.",
    )

    assert result == []


def test_repeated_page_furniture_is_removed_only_at_page_edges():
    pages = [
        {
            "page_number": page_number,
            "text": (
                "\n".join(
                    f"Body line {line_number} on page {page_number}."
                    for line_number in range(1, 10)
                )
                + "\n"
                "Copyright 2016, Industrial Press, Inc.\n"
                "http://ebooks.industrialpress.com\n"
                "Machinery's Handbook 30th Edition"
            ),
        }
        for page_number in range(1, 5)
    ]

    furniture = detect_repeated_page_furniture(pages)

    assert furniture == {
        "copyright 2016, industrial press, inc.",
        "http://ebooks.industrialpress.com",
        "machinery's handbook 30th edition",
    }
    filtered = strip_repeated_page_furniture(pages[0]["text"], furniture)
    assert "Body line 1 on page 1." in filtered
    assert "Body line 9 on page 1." in filtered
    assert "Copyright 2016" not in filtered


def test_furniture_text_is_preserved_when_it_occurs_inside_page_body():
    pages = [
        {
            "page_number": page_number,
            "text": (
                "Opening line.\n"
                "First body line.\n"
                "Second body line.\n"
                "Third body line.\n"
                "Machinery's Handbook 30th Edition\n"
                "A citation discusses the title above.\n"
                "Sixth body line.\n"
                "Seventh body line.\n"
                "Eighth body line.\n"
                f"Closing body line {page_number}.\n"
                "Repeated footer text"
            ),
        }
        for page_number in range(1, 5)
    ]

    furniture = detect_repeated_page_furniture(pages)
    filtered = strip_repeated_page_furniture(pages[0]["text"], furniture)

    assert "Machinery's Handbook 30th Edition" in filtered
    assert "Repeated footer text" not in filtered


def test_furniture_suffix_is_removed_without_deleting_preceding_content():
    page_text = (
        "\n".join(f"Body line {index}." for index in range(1, 10))
        + "\n"
        "xlog xCopyright 2016, Industrial Press, Inc.\n"
        "http://ebooks.industrialpress.com\n"
        "Machinery's Handbook 30th Edition"
    )
    furniture = {
        "copyright 2016, industrial press, inc.",
        "http://ebooks.industrialpress.com",
        "machinery's handbook 30th edition",
    }

    filtered = strip_repeated_page_furniture(page_text, furniture)

    assert filtered.rstrip().endswith("xlog x")
    assert "Copyright 2016" not in filtered


def test_sparse_furniture_only_page_is_fully_removed():
    page_text = (
        "Copyright 2016, Industrial Press, Inc.\n"
        "http://ebooks.industrialpress.com\n"
        "Machinery's Handbook 30th Edition"
    )
    furniture = {
        "copyright 2016, industrial press, inc.",
        "http://ebooks.industrialpress.com",
        "machinery's handbook 30th edition",
    }

    filtered = strip_repeated_page_furniture(page_text, furniture)

    assert filtered.strip() == ""


def test_build_chunks_filters_furniture_without_losing_source_spans():
    cleaned_text = "\n".join(
        (
            f"--- PAGE {page_number} ---\n"
            "DISCUSSION\n"
            + "\n".join(
                f"body line {line_number} for page {page_number}."
                for line_number in range(1, 9)
            )
            + "\n"
            "Copyright 2016, Industrial Press, Inc.\n"
            "http://ebooks.industrialpress.com\n"
            "Machinery's Handbook 30th Edition"
        )
        for page_number in range(1, 5)
    )

    result = build_chunks("document_123", cleaned_text)

    assert len(result) == 4
    assert all("Copyright" not in chunk["text"] for chunk in result)
    assert all("industrialpress.com" not in chunk["text"] for chunk in result)
    assert all("Handbook 30th" not in chunk["text"] for chunk in result)
    assert all(
        cleaned_text[
            chunk["source_char_start"]:chunk["source_char_end"]
        ] == chunk["text"]
        for chunk in result
    )


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


def test_retrieval_children_share_semantic_unit_identity():
    cleaned_text = (
        "--- PAGE 1 ---\n"
        "DISCUSSION\n"
        "First sentence has enough text to form a child. "
        "Second sentence has enough text to form another child. "
        "Third sentence finishes the semantic unit."
    )

    result = build_chunks("document_123", cleaned_text, max_chars=65)

    assert len(result) == 3
    assert {
        chunk["semantic_unit_id"]
        for chunk in result
    } == {"document_123_unit_0001"}
    assert [chunk["retrieval_chunk_index"] for chunk in result] == [1, 2, 3]
    assert all(chunk["retrieval_chunk_count"] == 3 for chunk in result)


def test_semantic_unit_identity_does_not_depend_on_retrieval_chunk_size():
    cleaned_text = (
        "--- PAGE 1 ---\n"
        "DISCUSSION\n"
        "First sentence belongs to the unit. "
        "Second sentence belongs to the same unit. "
        "Third sentence also belongs to the unit."
    )

    smaller_chunks = build_chunks("document_123", cleaned_text, max_chars=55)
    larger_chunks = build_chunks("document_123", cleaned_text, max_chars=500)

    assert len(smaller_chunks) > len(larger_chunks)
    assert {
        chunk["semantic_unit_id"]
        for chunk in smaller_chunks
    } == {
        chunk["semantic_unit_id"]
        for chunk in larger_chunks
    } == {"document_123_unit_0001"}


def test_matching_structure_continues_one_semantic_unit_across_pages():
    cleaned_text = (
        "--- PAGE 1 ---\n"
        "DISCUSSION\n"
        "the first page begins the explanation.\n"
        "--- PAGE 2 ---\n"
        "the second page continues the explanation.\n"
        "--- PAGE 3 ---\n"
        "RESULTS\n"
        "a new section begins here."
    )

    result = build_chunks("document_123", cleaned_text)
    discussion_chunks = result[:2]

    assert len(result) == 3
    assert {
        chunk["semantic_unit_id"]
        for chunk in discussion_chunks
    } == {"document_123_unit_0001"}
    assert [
        chunk["retrieval_chunk_index"]
        for chunk in discussion_chunks
    ] == [1, 2]
    assert all(
        chunk["retrieval_chunk_count"] == 2
        for chunk in discussion_chunks
    )
    assert all(
        chunk["semantic_unit_page_start"] == 1
        for chunk in discussion_chunks
    )
    assert all(
        chunk["semantic_unit_page_end"] == 2
        for chunk in discussion_chunks
    )
    assert all(
        chunk["semantic_unit_char_count"]
        == sum(len(child["text"]) for child in discussion_chunks)
        for chunk in discussion_chunks
    )
    assert all(
        chunk["semantic_unit_block_count"] == 2
        for chunk in discussion_chunks
    )
    assert all(
        cleaned_text[
            chunk["source_char_start"]:chunk["source_char_end"]
        ] == chunk["text"]
        for chunk in discussion_chunks
    )
    assert result[2]["semantic_unit_id"] == "document_123_unit_0002"


def test_semantic_units_do_not_cross_duplicate_section_provenance():
    blocks = [
        {
            "page_number": 10,
            "heading": "Introduction",
            "subheading": None,
            "major_section": "FIRST MAJOR",
            "category": "FIRST CATEGORY",
            "section_printed_page": 10,
            "text": "first introduction",
        },
        {
            "page_number": 11,
            "heading": "Introduction",
            "subheading": None,
            "major_section": "SECOND MAJOR",
            "category": "SECOND CATEGORY",
            "section_printed_page": 11,
            "text": "second introduction",
        },
    ]

    units = group_blocks_into_semantic_units(blocks)

    assert len(units) == 2


def test_unlabelled_blocks_remain_separate_semantic_units():
    blocks = [
        {
            "page_number": 1,
            "heading": None,
            "subheading": None,
            "text": "first front-matter block",
        },
        {
            "page_number": 2,
            "heading": None,
            "subheading": None,
            "text": "second front-matter block",
        },
    ]

    units = group_blocks_into_semantic_units(blocks)

    assert len(units) == 2


def test_bare_heuristic_headings_do_not_continue_across_pages():
    blocks = [
        {
            "page_number": 20,
            "heading": "SIZE",
            "subheading": None,
            "section_printed_page": None,
            "text": "first table page",
        },
        {
            "page_number": 21,
            "heading": "SIZE",
            "subheading": None,
            "section_printed_page": None,
            "text": "second table page",
        },
    ]

    units = group_blocks_into_semantic_units(blocks)

    assert len(units) == 2


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


def test_ambiguous_toc_hierarchy_does_not_resolve_to_future_section():
    lookup = build_toc_hierarchy_lookup(
        [
            {"title": "Introduction", "printed_page": 342},
            {"title": "Introduction", "printed_page": 1128},
        ]
    )

    assert resolve_toc_hierarchy(
        "Introduction",
        physical_page=203,
        hierarchy_lookup=lookup,
        printed_page_offset=12,
    ) == {}


def test_unique_toc_hierarchy_does_not_resolve_to_future_section():
    lookup = build_toc_hierarchy_lookup(
        [{"title": "Pressure", "printed_page": 2669}]
    )

    assert resolve_toc_hierarchy(
        "Pressure",
        physical_page=298,
        hierarchy_lookup=lookup,
        printed_page_offset=12,
    ) == {}


def test_toc_heading_candidates_are_limited_to_nearby_section_starts():
    entries = [
        {"title": "Current Section", "printed_page": 100},
        {"title": "Two-page Lag", "printed_page": 98},
        {"title": "Pressure", "printed_page": 2669},
    ]

    assert toc_heading_candidates_for_page(
        entries,
        physical_page=112,
        printed_page_offset=12,
    ) == {"current section", "two-page lag"}


def test_far_future_toc_title_does_not_promote_table_label():
    cleaned_text = (
        "--- PAGE 1 ---\n"
        "TABLE OF CONTENTS\n"
        "Each section includes a detailed table of contents\n"
        "MATHEMATICS 1\n"
        "\n"
        "--- PAGE 2 ---\n"
        "TABLE OF CONTENTS\n"
        "EXAMPLE CATEGORY\n"
        "10 Alpha\n"
        "20 Beta\n"
        "30 Gamma\n"
        "1000 Pressure\n"
        "\n"
        "--- PAGE 22 ---\n"
        "Alpha\n"
        "Alpha body.\n"
        "\n"
        "--- PAGE 32 ---\n"
        "Beta\n"
        "Beta body.\n"
        "\n"
        "--- PAGE 42 ---\n"
        "Gamma\n"
        "Gamma body.\n"
        "\n"
        "--- PAGE 50 ---\n"
        "Pressure\n"
        "Allowed, psi\n"
    )

    chunks = build_chunks("document_123", cleaned_text)
    page_50 = [chunk for chunk in chunks if chunk["page_start"] == 50]

    assert all(chunk["section_heading"] != "Pressure" for chunk in page_50)
    assert any("Pressure" in chunk["text"] for chunk in page_50)


def test_toc_category_ignores_repeated_major_section_header():
    cleaned_text = (
        "--- PAGE 1 ---\n"
        "TABLE OF CONTENTS\n"
        "Each section includes a detailed table of contents\n"
        "MACHINE ELEMENTS 100\n"
        "\n"
        "--- PAGE 10 ---\n"
        "TABLE OF CONTENTS\n"
        "MACHINE ELEMENTS\n"
        "(Continued)\n"
        "FLEXIBLE BELTS AND SHEAVES\n"
        "112 Sheave and Groove Dimensions\n"
    )

    entries = extract_toc_hierarchy(cleaned_text)

    assert entries[-1]["category"] == "FLEXIBLE BELTS AND SHEAVES"


def test_toc_category_persists_across_consecutive_toc_pages():
    cleaned_text = (
        "--- PAGE 1 ---\n"
        "TABLE OF CONTENTS\n"
        "Each section includes a detailed table of contents\n"
        "MACHINE ELEMENTS 100\n"
        "\n"
        "--- PAGE 10 ---\n"
        "TABLE OF CONTENTS\n"
        "FLEXIBLE BELTS AND SHEAVES\n"
        "112 Sheave and Groove Dimensions\n"
        "\n"
        "--- PAGE 11 ---\n"
        "TABLE OF CONTENTS\n"
        "MACHINE ELEMENTS\n"
        "(Continued)\n"
        "113 Standard Effective Lengths\n"
    )

    entries = extract_toc_hierarchy(cleaned_text)

    assert entries[-1]["category"] == "FLEXIBLE BELTS AND SHEAVES"


def test_major_section_name_can_complete_multiline_category():
    cleaned_text = (
        "--- PAGE 1 ---\n"
        "TABLE OF CONTENTS\n"
        "Each section includes a detailed table of contents\n"
        "FASTENERS 100\n"
        "\n"
        "--- PAGE 10 ---\n"
        "TABLE OF CONTENTS\n"
        "FASTENERS\n"
        "METRIC THREADED\n"
        "(Continued)\n"
        "FASTENERS\n"
        "112 Comparison with ISO Standards\n"
    )

    entries = extract_toc_hierarchy(cleaned_text)

    assert entries[-1]["category"] == "METRIC THREADED FASTENERS"


def test_build_chunks_separates_section_and_estimated_printed_pages():
    cleaned_text = (
        "--- PAGE 1 ---\n"
        "TABLE OF CONTENTS\n"
        "Each section includes a detailed table of contents\n"
        "MATHEMATICS 1\n"
        "\n"
        "--- PAGE 2 ---\n"
        "TABLE OF CONTENTS\n"
        "EXAMPLE CATEGORY\n"
        "10 Alpha\n"
        "20 Beta\n"
        "30 Gamma\n"
        "\n"
        "--- PAGE 22 ---\n"
        "Alpha\n"
        "Alpha body text.\n"
        "\n"
        "--- PAGE 32 ---\n"
        "Beta\n"
        "Beta body text.\n"
        "\n"
        "--- PAGE 42 ---\n"
        "Gamma\n"
        "Gamma body text.\n"
    )

    chunks = build_chunks("document_123", cleaned_text)
    alpha = next(
        chunk for chunk in chunks
        if chunk["section_heading"] == "Alpha"
    )

    assert alpha["page_start"] == 22
    assert alpha["printed_page"] == 10
    assert alpha["section_printed_page"] == 10
    assert alpha["estimated_printed_page"] == 10
    assert alpha["printed_page_offset"] == 12
