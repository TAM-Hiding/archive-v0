import json

from ingestion.chunkers import (
    build_chunks,
    is_likely_heading,
    normalize_heading,
    parse_cleaned_text_into_pages,
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

    result = split_page_into_blocks(3, page_text)

    assert result == [
        {
            "page_number": 3,
            "heading": "INTRODUCTION",
            "text": "This is the introduction.",
        },
        {
            "page_number": 3,
            "heading": "RESULTS",
            "text": "These are the results.",
        },
    ]


def test_inline_abstract_heading():
    page_text = "Abstract: This paper describes a deterministic archive."

    result = split_page_into_blocks(1, page_text)

    assert result == [
        {
            "page_number": 1,
            "heading": "Abstract",
            "text": "This paper describes a deterministic archive.",
        }
    ]


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
