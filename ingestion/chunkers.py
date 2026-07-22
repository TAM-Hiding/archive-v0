from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import re


PAGE_MARKER_PATTERN = re.compile(r"^--- PAGE (\d+) ---$")

KNOWN_HEADINGS = {
    "abstract",
    "materials and methods",
    "results",
    "references",
    "further research",
    "acknowledgments",
    "introduction",
    "discussion",
    "conclusion",
}


def normalize_heading(text: str) -> str:
    """
    Normalize a heading candidate for matching.
    """
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def parse_cleaned_text_into_pages(cleaned_text: str) -> list[dict[str, Any]]:
    """
    Split cleaned text into page-numbered page blocks based on page markers.

    Expected marker format:
        --- PAGE 1 ---
    """
    lines = cleaned_text.splitlines()

    pages: list[dict[str, Any]] = []
    current_page_number: int | None = None
    current_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        match = PAGE_MARKER_PATTERN.match(stripped)

        if match:
            if current_page_number is not None:
                pages.append({
                    "page_number": current_page_number,
                    "text": "\n".join(current_lines).strip(),
                })

            current_page_number = int(match.group(1))
            current_lines = []
        else:
            current_lines.append(line)

    if current_page_number is not None:
        pages.append({
            "page_number": current_page_number,
            "text": "\n".join(current_lines).strip(),
        })

    return pages


def is_likely_heading(line: str) -> bool:
    """
    Conservative heading detection heuristic.

    Heading if:
    - matches a known heading, OR
    - strongly all-caps-ish
    """
    text = line.strip()
    if not text:
        return False

    if len(text) > 80:
        return False

    if text.endswith((".", ";", ",")):
        return False

    normalized = normalize_heading(text)
    if normalized in KNOWN_HEADINGS:
        return True

    letters_only = re.sub(r"[^A-Za-z]", "", text)
    if not letters_only:
        return False

    uppercase_ratio = sum(1 for c in letters_only if c.isupper()) / len(letters_only)
    return uppercase_ratio > 0.7


def split_page_into_blocks(page_number: int, page_text: str) -> list[dict[str, Any]]:
    """
    Split a page into heading-aware blocks.

    Each block is a dict with:
    - page_number
    - heading
    - text

    Special handling:
    - lines starting with inline heading markers like 'Abstract:'
      trigger a new heading block
    """
    lines = [line.rstrip() for line in page_text.splitlines()]
    blocks: list[dict[str, Any]] = []

    current_heading: str | None = None
    current_body_lines: list[str] = []

    def flush_block() -> None:
        nonlocal current_heading, current_body_lines
        block_text = "\n".join(current_body_lines).strip()
        if block_text:
            blocks.append({
                "page_number": page_number,
                "heading": current_heading,
                "text": block_text,
            })
        current_body_lines = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            current_body_lines.append("")
            continue

        # Inline heading marker handling, e.g. "Abstract: ..."
        lowered = stripped.lower()
        if lowered.startswith("abstract:"):
            flush_block()
            current_heading = "Abstract"
            abstract_body = stripped[len("abstract:"):].strip()
            if abstract_body:
                current_body_lines.append(abstract_body)
            continue

        if is_likely_heading(stripped):
            flush_block()
            current_heading = stripped
        else:
            current_body_lines.append(stripped)

    flush_block()
    return blocks


def split_text_into_paragraphs(text: str) -> list[str]:
    """
    Split a block into paragraphs using blank-line separation.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return paragraphs


def split_text_into_sentence_groups(text: str, target_chars: int = 900) -> list[str]:
    """
    Fallback splitter when paragraph structure is weak.

    Splits text into rough sentence groups aiming for target size.
    """
    text = text.strip()
    if not text:
        return []

    # Split after sentence-like punctuation followed by whitespace
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return [text]

    groups: list[str] = []
    current_parts: list[str] = []

    for sentence in sentences:
        candidate = " ".join(current_parts + [sentence]).strip()

        if current_parts and len(candidate) > target_chars:
            groups.append(" ".join(current_parts).strip())
            current_parts = [sentence]
        else:
            current_parts.append(sentence)

    if current_parts:
        groups.append(" ".join(current_parts).strip())

    return groups


def split_oversized_block(
    block: dict[str, Any],
    max_chars: int = 1200,
) -> list[dict[str, Any]]:
    """
    Split a large block into chunk-sized pieces.

    Strategy:
    1. try paragraph boundaries
    2. if that fails badly, use sentence-group fallback

    Keeps page_number and heading attached.
    """
    text = block["text"]
    if len(text) <= max_chars:
        return [block]

    paragraphs = split_text_into_paragraphs(text)

    # If paragraph splitting is weak (one giant paragraph), fall back
    if len(paragraphs) <= 1:
        sentence_groups = split_text_into_sentence_groups(text, target_chars=max_chars)
        return [
            {
                "page_number": block["page_number"],
                "heading": block["heading"],
                "text": group,
            }
            for group in sentence_groups
            if group.strip()
        ]

    chunks: list[dict[str, Any]] = []
    current_parts: list[str] = []

    for paragraph in paragraphs:
        candidate = "\n\n".join(current_parts + [paragraph]).strip()

        if current_parts and len(candidate) > max_chars:
            chunks.append({
                "page_number": block["page_number"],
                "heading": block["heading"],
                "text": "\n\n".join(current_parts).strip(),
            })
            current_parts = [paragraph]
        else:
            current_parts.append(paragraph)

    if current_parts:
        chunks.append({
            "page_number": block["page_number"],
            "heading": block["heading"],
            "text": "\n\n".join(current_parts).strip(),
        })

    return chunks


def apply_front_matter_rules(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Apply simple first-page/front-matter cleanup rules.

    For v1:
    - keep leading page-1 content before first real heading as front matter
    - if a block starts with 'Abstract:' and has no heading, treat it as Abstract
    """
    adjusted: list[dict[str, Any]] = []

    for block in blocks:
        text = block["text"].strip()
        heading = block["heading"]

        if heading is None and text.lower().startswith("abstract:"):
            block = {
                "page_number": block["page_number"],
                "heading": "Abstract",
                "text": text,
            }

        adjusted.append(block)

    return adjusted


def build_chunks(
    doc_id: str,
    cleaned_text: str,
    max_chars: int = 1200,
) -> list[dict[str, Any]]:
    """
    Full deterministic chunking pipeline.

    Returns a list of chunk dictionaries.
    """
    pages = parse_cleaned_text_into_pages(cleaned_text)

    raw_blocks: list[dict[str, Any]] = []
    for page in pages:
        page_blocks = split_page_into_blocks(page["page_number"], page["text"])
        raw_blocks.extend(page_blocks)

    raw_blocks = apply_front_matter_rules(raw_blocks)

    sized_blocks: list[dict[str, Any]] = []
    for block in raw_blocks:
        sized_blocks.extend(split_oversized_block(block, max_chars=max_chars))

    chunks: list[dict[str, Any]] = []

    current_offset = 0

    for index, block in enumerate(sized_blocks, start=1):
        block_text = block["text"]

        char_start = current_offset
        char_end = current_offset + len(block_text)

        chunks.append({
            "chunk_id": f"{doc_id}_chunk_{index:04d}",
            "doc_id": doc_id,
            "chunk_index": index,
            "page_start": block["page_number"],
            "page_end": block["page_number"],
            "section_heading": block["heading"],
            "text": block_text,
            "char_count": len(block_text),
            "char_start": char_start,
            "char_end": char_end,
        })

        current_offset = char_end

    return chunks


def save_chunks(output_path: str | Path, chunks: list[dict[str, Any]]) -> Path:
    """
    Save chunks to disk as pretty-printed JSON.
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)

    return output_file
