from __future__ import annotations

from collections import Counter, defaultdict
from math import ceil
from pathlib import Path
from typing import Any
import json
import re


PAGE_MARKER_PATTERN = re.compile(r"^--- PAGE (\d+) ---$")
PAGE_MARKER_SCAN_PATTERN = re.compile(
    r"^--- PAGE (\d+) ---[^\S\r\n]*$",
    re.MULTILINE,
)

TOC_NUMBERED_ENTRY_PATTERN = re.compile(r"^\s*(\d{1,4})\s+(.+?)\s*$")

GLOBAL_CONTENTS_SECTION_PATTERN = re.compile(
    r"^([A-Z][A-Z0-9\s,&/\-]+?)\s+(\d{1,4}|[IVXLCDMivxlcdm]+)$"
)
GLOBAL_CONTENTS_REVERSED_SECTION_PATTERN = re.compile(
    r"^(\d{1,4})([A-Z][A-Z0-9\s,&/\-]+)$"
)
ROMAN_FRONT_MATTER_PAGE_PATTERN = re.compile(r"^[ivxlcdm]{1,8}$")

TABLE_CAPTION_PATTERN = re.compile(
    r"^\s*Table\s+"
    r"(?:\d+(?:[.-]\d+)*[A-Za-z]?|[IVXLCDM]+)"
    r"(?:[.:])?(?:\s+.*)?$",
    re.IGNORECASE,
)

RUNNING_HEADER_PATTERNS = [
    re.compile(r"^\d+\s+[A-Z][A-Z0-9\s,&/\-]+$"),
    re.compile(r"^[A-Z][A-Z0-9\s,&/\-]+\s+\d+$"),
]


def is_running_page_header(line: str) -> bool:
    text = line.strip()

    if not text or len(text) > 100:
        return False

    letters = [char for char in text if char.isalpha()]
    alnum = [char for char in text if char.isalnum()]

    # Real running headers are overwhelmingly textual.
    # Reject equation/table rows containing only scattered letters.
    if len(letters) < 4:
        return False

    if not alnum:
        return False

    if len(letters) / len(alnum) < 0.5:
        return False

    return any(
        pattern.fullmatch(text)
        for pattern in RUNNING_HEADER_PATTERNS
    )


def normalize_heading(text: str) -> str:
    """
    Normalize a heading candidate for matching.
    """
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text

def looks_like_toc_page(page_text: str) -> bool:
    """
    Detect explicit table-of-contents pages.

    For now, require the source itself to identify the page as a TOC.
    This avoids mistaking tables, numbered procedures, equations,
    and reference data for structural navigation.
    """
    lines = [
        line.strip()
        for line in page_text.splitlines()
        if line.strip()
    ]

    return any(
        normalize_heading(line) == "table of contents"
        for line in lines[:5]
    )


def looks_like_global_contents_page(page_text: str) -> bool:
    """Return whether a front-matter page catalogs the book's major sections."""
    normalized = normalize_heading(page_text)
    instruction = "each section includes a detailed table of contents or index"

    if instruction not in normalized:
        return False

    return any(
        GLOBAL_CONTENTS_SECTION_PATTERN.fullmatch(line.strip())
        for line in page_text.splitlines()
    )


def looks_like_roman_front_matter_page(page_text: str) -> bool:
    """Detect a roman-numbered front-matter page near its leading edge."""
    leading_lines = [
        line.strip()
        for line in page_text.splitlines()
        if line.strip()
    ][:3]

    return any(
        ROMAN_FRONT_MATTER_PAGE_PATTERN.fullmatch(line)
        for line in leading_lines
    )


def strip_roman_front_matter_page_label(page_text: str) -> str:
    """Remove one leading roman page label without touching body numerals."""
    lines = page_text.splitlines()
    nonblank_seen = 0

    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        nonblank_seen += 1
        if ROMAN_FRONT_MATTER_PAGE_PATTERN.fullmatch(stripped):
            lines[index] = ""
            break

        if nonblank_seen >= 3:
            break

    return "\n".join(lines)


def split_global_contents_page_into_blocks(
    page_number: int,
    page_text: str,
) -> list[dict[str, Any]]:
    """Split the global contents catalog at major-section boundaries.

    Wrapped bullet lists belong to the preceding major section. Keeping them
    together prevents ordinary all-caps heading heuristics and running-header
    detection from shredding the catalog into tiny, misleading entries.
    """
    page_label: str | None = None
    preamble_lines: list[str] = []
    sections: list[tuple[str, list[str]]] = []
    current_title: str | None = None
    current_lines: list[str] = []

    def flush_section() -> None:
        nonlocal current_title, current_lines
        if current_title is not None and current_lines:
            sections.append((current_title, current_lines))
        current_title = None
        current_lines = []

    for line in page_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        normalized = normalize_heading(stripped)
        if normalized == "table of contents":
            continue

        if ROMAN_FRONT_MATTER_PAGE_PATTERN.fullmatch(stripped):
            page_label = stripped
            continue

        if normalized.startswith(
            "each section includes a detailed table of contents or index"
        ):
            preamble_lines.append(stripped)
            continue

        section_match = GLOBAL_CONTENTS_SECTION_PATTERN.fullmatch(stripped)
        reversed_match = GLOBAL_CONTENTS_REVERSED_SECTION_PATTERN.fullmatch(
            stripped
        )

        if section_match is not None:
            section_title = section_match.group(1).strip()
            page_reference = section_match.group(2)

            # License, preface, and acknowledgments are one compact front-
            # matter group rather than several nearly empty catalog entries.
            if ROMAN_FRONT_MATTER_PAGE_PATTERN.fullmatch(page_reference.lower()):
                if current_title != "Front Matter":
                    flush_section()
                    current_title = "Front Matter"
                current_lines.append(stripped)
            else:
                flush_section()
                current_title = section_title
                current_lines = [stripped]
            continue

        if reversed_match is not None:
            flush_section()
            current_title = reversed_match.group(2).strip()
            current_lines = [stripped]
            continue

        if current_title is None:
            preamble_lines.append(stripped)
        else:
            current_lines.append(stripped)

    flush_section()

    running_header = "TABLE OF CONTENTS"
    if page_label:
        running_header = f"{running_header} {page_label}"

    if sections and preamble_lines:
        title, lines = sections[0]
        sections[0] = (title, preamble_lines + lines)
        preamble_lines = []

    blocks = [
        {
            "page_number": page_number,
            "heading": "Table of Contents",
            "subheading": title,
            "running_header": running_header,
            "content_type": "contents",
            "text": "\n".join(lines),
        }
        for title, lines in sections
        if lines
    ]

    if preamble_lines:
        blocks.insert(0, {
            "page_number": page_number,
            "heading": "Table of Contents",
            "subheading": None,
            "running_header": running_header,
            "content_type": "contents",
            "text": "\n".join(preamble_lines),
        })

    return blocks

def extract_toc_heading_candidates(cleaned_text: str) -> set[str]:
    """
    Extract normalized semantic heading candidates from numbered TOC entries.

    Example:
        '14 Logarithms'
        -> 'logarithms'

        '15 Imaginary and Complex Numbers'
        -> 'imaginary and complex numbers'
    """
    pages = parse_cleaned_text_into_pages(cleaned_text)

    candidates: set[str] = set()

    for page in pages:
        if not looks_like_toc_page(page["text"]):
            continue

        for line in page["text"].splitlines():
            stripped = line.strip()
            match = TOC_NUMBERED_ENTRY_PATTERN.match(stripped)

            if not match:
                continue

            title = match.group(2).strip()

            if not title:
                continue

            if len(title) > 100:
                continue

            if title.endswith((".", ";", ",")):
                continue

            if not re.search(r"[A-Za-z]", title):
                continue

            candidates.add(normalize_heading(title))

    return candidates

def extract_toc_hierarchy(cleaned_text: str) -> list[dict[str, Any]]:
    """
    Extract a first-pass hierarchy from explicit TOC pages.

    Returns records shaped like:

        {
            "toc_page": 13,
            "category": "NUMBERS, FRACTIONS, AND DECIMALS",
            "title": "Logarithms",
            "printed_page": 14,
        }

    This does not yet modify chunks. It only builds structural metadata.
    """
    pages = parse_cleaned_text_into_pages(cleaned_text)
    entries: list[dict[str, Any]] = []
    major_section_titles = {
        normalize_heading(section["title"])
        for section in extract_major_toc_sections(cleaned_text)
        if section.get("title")
    }
    current_category: str | None = None
    previous_toc_page: int | None = None

    for page in pages:
        if not looks_like_toc_page(page["text"]):
            continue

        if (
            previous_toc_page is None
            or page["page_number"] != previous_toc_page + 1
        ):
            current_category = None

        previous_toc_page = page["page_number"]

        lines = [
            line.strip()
            for line in page["text"].splitlines()
            if line.strip()
        ]

        pending_category_parts: list[str] = []

        for line in lines:
            normalized = normalize_heading(line)

            if normalized == "table of contents":
                continue

            if normalized in {"continued", "(continued)"}:
                continue

            # Repeated major-section names are page-level navigation headers,
            # not part of the local TOC category.
            if normalized in major_section_titles and not pending_category_parts:
                continue

            match = TOC_NUMBERED_ENTRY_PATTERN.match(line)

            if match:
                # Finish any multi-line uppercase category before
                # attaching this numbered entry to it.
                if pending_category_parts:
                    current_category = " ".join(pending_category_parts)
                    pending_category_parts = []

                printed_page = int(match.group(1))
                title = match.group(2).strip()

                if not title:
                    continue

                if len(title) > 100:
                    continue

                if title.endswith((".", ";", ",")):
                    continue

                if not re.search(r"[A-Za-z]", title):
                    continue

                entries.append({
                    "toc_page": page["page_number"],
                    "category": current_category,
                    "title": title,
                    "printed_page": printed_page,
                })

                continue

            # Uppercase TOC lines act as category headings.
            letters = [char for char in line if char.isalpha()]

            if (
                letters
                and len(line) <= 100
                and line.upper() == line
            ):
                pending_category_parts.append(line)
                continue

            # A normal non-numbered, non-uppercase line ends a pending
            # category heading.
            if pending_category_parts:
                current_category = " ".join(pending_category_parts)
                pending_category_parts = []

    return entries

def extract_major_toc_sections(cleaned_text: str) -> list[dict[str, Any]]:
    """
    Extract major handbook sections from the global table of contents.

    Returns records like:

        {
            "title": "MATHEMATICS",
            "printed_page": 1,
        }

        {
            "title": "TOOLING AND TOOLMAKING",
            "printed_page": 803,
        }
    """
    pages = parse_cleaned_text_into_pages(cleaned_text)
    sections: list[dict[str, Any]] = []

    global_toc_phrase = "each section includes a detailed table of contents"

    for page in pages:
        page_normalized = normalize_heading(page["text"])

        if global_toc_phrase not in page_normalized:
            continue

        for line in page["text"].splitlines():
            stripped = line.strip()

            match = re.match(
                r"^([A-Z][A-Z0-9\s,&/\-]+?)\s+(\d{1,4})$",
                stripped,
            )

            if not match:
                continue

            title = match.group(1).strip()
            printed_page = int(match.group(2))

            if title == "TABLE OF CONTENTS":
                continue

            sections.append({
                "title": title,
                "printed_page": printed_page,
            })

    sections.sort(key=lambda item: item["printed_page"])
    return sections

def attach_major_sections_to_toc_entries(
    entries: list[dict[str, Any]],
    major_sections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Attach each TOC entry to the major handbook section whose
    printed-page range contains that entry.
    """
    if not major_sections:
        return entries

    sorted_sections = sorted(
        major_sections,
        key=lambda item: item["printed_page"],
    )

    enriched: list[dict[str, Any]] = []

    for entry in entries:
        printed_page = entry.get("printed_page")
        major_section: str | None = None

        if printed_page is not None:
            for section in sorted_sections:
                if section["printed_page"] <= printed_page:
                    major_section = section["title"]
                else:
                    break

        enriched.append({
            **entry,
            "major_section": major_section,
        })

    return enriched

def build_toc_hierarchy_lookup(
    entries: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """
    Build a lossless normalized heading lookup for TOC hierarchy metadata.

    Example:
        "logarithms" -> [{...}]

    A title can occur in multiple document locations. Preserve every
    candidate here so document position can resolve the correct record.
    """
    lookup: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for entry in entries:
        title = entry.get("title")

        if not title:
            continue

        key = normalize_heading(title)

        lookup[key].append({
            "major_section": entry.get("major_section"),
            "category": entry.get("category"),
            "printed_page": entry.get("printed_page"),
        })

    return dict(lookup)


def infer_printed_page_offset(
    pages: list[dict[str, Any]],
    toc_entries: list[dict[str, Any]],
) -> int | None:
    """Infer physical-PDF-page minus printed-page alignment.

    Only unambiguous TOC titles and exact standalone body lines vote. If
    fewer than three records agree on the most common offset, the document
    does not provide enough evidence and ambiguous hierarchy stays unset.
    """
    entries_by_title: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in toc_entries:
        title = entry.get("title")
        printed_page = entry.get("printed_page")
        if title and printed_page is not None:
            entries_by_title[normalize_heading(title)].append(entry)

    body_pages_by_line: dict[str, set[int]] = defaultdict(set)
    for page in pages:
        if looks_like_toc_page(page["text"]):
            continue
        for line in page["text"].splitlines():
            stripped = line.strip()
            if stripped:
                body_pages_by_line[normalize_heading(stripped)].add(
                    page["page_number"]
                )

    offsets: list[int] = []
    for title, entries in entries_by_title.items():
        body_pages = body_pages_by_line.get(title, set())
        if len(entries) != 1 or len(body_pages) != 1:
            continue

        physical_page = next(iter(body_pages))
        printed_page = entries[0]["printed_page"]
        offsets.append(physical_page - printed_page)

    if not offsets:
        return None

    ranked_offsets = Counter(offsets).most_common(2)
    offset, votes = ranked_offsets[0]
    if votes < 3:
        return None

    if len(ranked_offsets) > 1 and ranked_offsets[1][1] == votes:
        return None

    return offset


def toc_heading_candidates_for_page(
    toc_entries: list[dict[str, Any]],
    physical_page: int,
    printed_page_offset: int | None,
    max_start_lag: int = 2,
) -> set[str]:
    """Return TOC headings eligible to begin near one physical page.

    A global TOC title set lets ordinary table labels promote sections
    thousands of pages early. Require source-position agreement instead.
    """
    if printed_page_offset is None:
        return set()

    estimated_printed_page = physical_page - printed_page_offset
    candidates: set[str] = set()

    for entry in toc_entries:
        title = entry.get("title")
        section_start = entry.get("printed_page")

        if not title or section_start is None:
            continue

        if section_start <= estimated_printed_page <= section_start + max_start_lag:
            candidates.add(normalize_heading(title))

    return candidates


def resolve_toc_hierarchy(
    heading: str | None,
    physical_page: int,
    hierarchy_lookup: dict[str, list[dict[str, Any]]],
    printed_page_offset: int | None,
) -> dict[str, Any]:
    """Resolve one hierarchy record without silently discarding duplicates."""
    candidates = hierarchy_lookup.get(normalize_heading(heading or ""), [])

    if not candidates or printed_page_offset is None:
        return {}

    estimated_printed_page = physical_page - printed_page_offset
    positioned = [
        candidate
        for candidate in candidates
        if candidate.get("printed_page") is not None
    ]

    if not positioned:
        return {}

    preceding = [
        candidate
        for candidate in positioned
        if candidate["printed_page"] <= estimated_printed_page
    ]

    if preceding:
        return max(preceding, key=lambda item: item["printed_page"])

    return {}

def parse_cleaned_text_into_pages(cleaned_text: str) -> list[dict[str, Any]]:
    """
    Split cleaned text into page-numbered page blocks based on page markers.

    Expected marker format:
        --- PAGE 1 ---
    """
    pages: list[dict[str, Any]] = []
    markers = list(PAGE_MARKER_SCAN_PATTERN.finditer(cleaned_text))

    for index, marker in enumerate(markers):
        raw_start = marker.end()
        raw_end = (
            markers[index + 1].start()
            if index + 1 < len(markers)
            else len(cleaned_text)
        )
        raw_page_text = cleaned_text[raw_start:raw_end]
        leading_whitespace = len(raw_page_text) - len(raw_page_text.lstrip())
        trailing_whitespace = len(raw_page_text) - len(raw_page_text.rstrip())
        source_char_start = raw_start + leading_whitespace
        source_char_end = raw_end - trailing_whitespace

        pages.append({
            "page_number": int(marker.group(1)),
            "text": cleaned_text[source_char_start:source_char_end],
            "source_char_start": source_char_start,
            "source_char_end": source_char_end,
        })

    return pages


def page_margin_line_indexes(
    lines: list[str],
    margin_line_count: int = 3,
) -> set[int]:
    """Return conservative nonblank line indexes at the page edges."""
    if margin_line_count <= 0:
        return set()

    nonblank_indexes = [
        index
        for index, line in enumerate(lines)
        if line.strip()
    ]

    if not nonblank_indexes:
        return set()

    effective_margin_count = min(
        margin_line_count,
        max(1, len(nonblank_indexes) // 4),
    )
    return set(
        nonblank_indexes[:effective_margin_count]
        + nonblank_indexes[-effective_margin_count:]
    )


def detect_repeated_page_furniture(
    pages: list[dict[str, Any]],
    margin_line_count: int = 3,
    min_repetitions: int = 3,
    min_page_fraction: float = 0.10,
) -> set[str]:
    """Detect exact repeated text confined to page-edge line candidates.

    Keys must recur on a meaningful fraction of distinct pages. This catches
    stable book footers without treating short table continuations, citations,
    or one-off URLs as disposable content.
    """
    if not pages:
        return set()

    required_pages = max(
        min_repetitions,
        ceil(len(pages) * min_page_fraction),
    )
    page_counts: Counter[str] = Counter()

    for page in pages:
        lines = page.get("text", "").splitlines()
        margin_indexes = page_margin_line_indexes(
            lines,
            margin_line_count,
        )
        page_keys = {
            normalize_heading(lines[index])
            for index in margin_indexes
            if len(lines[index].strip()) <= 160
            and re.search(r"[A-Za-z]", lines[index])
        }
        page_counts.update(page_keys)

    return {
        key
        for key, count in page_counts.items()
        if count >= required_pages
    }


def strip_repeated_page_furniture(
    page_text: str,
    furniture_keys: set[str],
    margin_line_count: int = 3,
) -> str:
    """Remove detected furniture only when it occurs at this page's edges."""
    if not furniture_keys:
        return page_text

    lines = page_text.splitlines()
    nonblank_indexes = [
        index
        for index, line in enumerate(lines)
        if line.strip()
    ]
    margin_indexes = page_margin_line_indexes(
        lines,
        margin_line_count,
    )

    if nonblank_indexes and all(
        normalize_heading(lines[index]) in furniture_keys
        for index in nonblank_indexes
    ):
        margin_indexes = set(nonblank_indexes)

    for index in margin_indexes:
        for key in sorted(furniture_keys, key=len, reverse=True):
            suffix_pattern = re.compile(
                r"\s*"
                + r"\s+".join(
                    re.escape(token)
                    for token in key.split()
                )
                + r"\s*$",
                re.IGNORECASE,
            )
            match = suffix_pattern.search(lines[index])

            if match is not None:
                lines[index] = lines[index][:match.start()].rstrip()
                break

    return "\n".join(lines)


def find_source_text_span(
    text: str,
    source_text: str,
    start_at: int = 0,
) -> tuple[int, int] | None:
    """Locate normalized chunk text in its source page.

    Chunking may normalize line and paragraph whitespace, so match the
    original non-whitespace tokens while allowing source whitespace between
    them. Callers advance ``start_at`` to disambiguate repeated table rows.
    """
    tokens = re.findall(r"\S+", text)
    if not tokens:
        return None

    pattern = r"\s+".join(re.escape(token) for token in tokens)
    match = re.search(pattern, source_text[start_at:], re.DOTALL)
    if match is None:
        return None

    return start_at + match.start(), start_at + match.end()

KNOWN_HEADINGS = {
    "abstract",
    "acknowledgments",
    "introduction",
    "background",
    "methods",
    "methodology",
    "results",
    "discussion",
    "conclusion",
    "conclusions",
    "references",
    "bibliography",
    "appendix",
    "preface",
    "table of contents",
}


def is_display_math_line(text: str) -> bool:
    """Return whether a short line is visibly mathematical, not a heading."""
    stripped = text.strip()
    if not stripped:
        return False

    if re.search(r"-{5,}", stripped):
        return True

    if any(operator in stripped for operator in ("=", "×", "÷", "≤", "≥")):
        return True

    return False


def equation_layout_hint(text: str) -> str:
    """Mark chunks whose extracted line breaks carry equation structure."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    fraction_bar_count = sum(
        1 for line in lines if re.search(r"-{5,}", line)
    )
    equation_line_count = sum(
        1 for line in lines
        if "=" in line and re.search(r"[A-Za-z0-9]", line)
    )

    if fraction_bar_count or equation_line_count >= 2:
        return "equation"

    return ""

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

    if is_display_math_line(text):
        return False

    normalized = normalize_heading(text)
    if normalized in KNOWN_HEADINGS:
        return True

    letters_only = re.sub(r"[^A-Za-z]", "", text)
    if not letters_only:
        return False

    words = re.findall(r"[A-Za-z]+", text)
    letters = [char for char in text if char.isalpha()]
    alnum = [char for char in text if char.isalnum()]

    if not words:
        return False

    # Reject formula labels like P10 / C52 and table rows
    # containing only isolated letter codes.
    if max(len(word) for word in words) < 3:
        return False

    if alnum and len(letters) / len(alnum) < 0.5:
        return False

    uppercase_ratio = sum(
        1 for c in letters_only if c.isupper()
    ) / len(letters_only)

    return uppercase_ratio > 0.7
    
INLINE_SUBHEADING_PATTERN = re.compile(
    r"^(.+?)\.\-\s*(.*)$"
)

def extract_inline_subheading(
    line: str,
    toc_heading_candidates: set[str] | None = None,
) -> tuple[str | None, str]:
    """
    Detect Handbook-style inline subsection headings such as:

        Permutations.-The number of ways...
        Combinations.-Arranging objects...
        Operations on Complex Numbers.-Example 1...

    Returns:
        (subheading, body_text)

    If no inline subheading is detected:
        (None, original_line)
    """
    stripped = line.strip()

    match = INLINE_SUBHEADING_PATTERN.match(stripped)
    if not match:
        return None, stripped

    candidate = match.group(1).strip()
    body = match.group(2).strip()

    if not candidate:
        return None, stripped

    # Keep this deliberately conservative.
    if len(candidate) > 100:
        return None, stripped

    if not re.search(r"[A-Za-z]", candidate):
        return None, stripped

    return candidate, body

def match_toc_section_heading(
    text: str,
    toc_heading_candidates: set[str],
) -> str | None:
    """
    Match a body heading against authoritative TOC headings.

    Allows only conservative editorial expansions such as:
        Factorial -> Factorial Notation
        Prime Numbers and Factors -> Prime Numbers and Factors of Numbers
    """
    normalized = normalize_heading(text)

    if normalized in toc_heading_candidates:
        return normalized

    allowed_suffixes = {
        " notation",
        " of numbers",
    }

    for candidate in toc_heading_candidates:
        if not normalized.startswith(candidate):
            continue

        suffix = normalized[len(candidate):]

        if suffix in allowed_suffixes:
            return candidate

    return None

def split_page_into_blocks(
    page_number: int,
    page_text: str,
    inherited_heading: str | None = None,
    inherited_subheading: str | None = None,
    toc_heading_candidates: set[str] | None = None,
    toc_heading_lookup: dict[str, str] | None = None,
    allow_heuristic_headings: bool = True,
) -> tuple[list[dict[str, Any]], str | None, str | None]:
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
    
    if toc_heading_candidates is None:
        toc_heading_candidates = set()
    
    if toc_heading_lookup is None:
        toc_heading_lookup = {}

    current_heading: str | None = inherited_heading
    current_subheading: str | None = inherited_subheading
    current_running_header: str | None = None
    current_body_lines: list[str] = []

    def flush_block() -> None:
        nonlocal current_heading, current_running_header, current_body_lines
        block_text = "\n".join(current_body_lines).strip()
        if block_text:
            blocks.append({
                "page_number": page_number,
                "heading": current_heading,
                "subheading": current_subheading,
                "running_header": current_running_header,
                "text": block_text,
            })
        current_body_lines = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            current_body_lines.append("")
            continue
        
        if is_running_page_header(stripped):
            flush_block()
            current_running_header = stripped
            continue

        matched_toc_heading = match_toc_section_heading(
            stripped,
            toc_heading_candidates,
        )

        if matched_toc_heading is not None:
            flush_block()

            exact_match = normalize_heading(stripped) == matched_toc_heading

            canonical_heading = toc_heading_lookup.get(
                matched_toc_heading,
                stripped if exact_match else matched_toc_heading,
            )

            if exact_match:
                current_heading = canonical_heading
                current_subheading = None
            else:
                # Editorially expanded body heading, e.g.:
                # "Prime Numbers and Factors of Numbers"
                current_heading = canonical_heading
                current_subheading = stripped

            continue

        # Inline heading marker handling, e.g. "Abstract: ..."
        lowered = stripped.lower()
        if lowered.startswith("abstract:"):
            flush_block()
            current_heading = "Abstract"
            current_subheading = None
            abstract_body = stripped[len("abstract:"):].strip()
            if abstract_body:
                current_body_lines.append(abstract_body)
            continue

        if (
            is_likely_heading(stripped)
            and (
                allow_heuristic_headings
                or normalize_heading(stripped) in KNOWN_HEADINGS
            )
        ):
            flush_block()
            current_heading = stripped
            current_subheading = None
            continue

        inline_subheading, inline_body = extract_inline_subheading(
            stripped,
            toc_heading_candidates=toc_heading_candidates,
        )

        if inline_subheading is not None:
            flush_block()

            matched_toc_heading = match_toc_section_heading(
                inline_subheading,
                toc_heading_candidates,
            )

            if matched_toc_heading is not None:
                canonical_heading = toc_heading_lookup.get(
                    matched_toc_heading,
                    matched_toc_heading,
                )

                if normalize_heading(inline_subheading) == matched_toc_heading:
                    current_heading = canonical_heading
                    current_subheading = None
                else:
                    current_heading = canonical_heading
                    current_subheading = inline_subheading
            else:
                current_subheading = inline_subheading

            if inline_body:
                current_body_lines.append(inline_body)

            continue

        current_body_lines.append(stripped)

    flush_block()
    return blocks, current_heading, current_subheading

def split_text_into_paragraphs(text: str) -> list[str]:
    """
    Split a block into paragraphs using blank-line separation.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return paragraphs


def split_block_at_table_captions(
    block: dict[str, Any],
) -> list[dict[str, Any]]:
    """Separate prose and caption-led tables into distinct source blocks."""
    lines = block["text"].splitlines()
    caption_indexes = [
        index
        for index, line in enumerate(lines)
        if TABLE_CAPTION_PATTERN.fullmatch(line.strip())
    ]

    if not caption_indexes:
        return [{
            **block,
            "content_type": block.get("content_type", "prose"),
            "table_caption": block.get("table_caption"),
        }]

    separated: list[dict[str, Any]] = []
    first_caption_index = caption_indexes[0]
    prose_text = "\n".join(lines[:first_caption_index]).strip()

    if prose_text:
        separated.append({
            **block,
            "content_type": "prose",
            "table_caption": None,
            "text": prose_text,
        })

    for caption_position, caption_index in enumerate(caption_indexes):
        next_caption_index = (
            caption_indexes[caption_position + 1]
            if caption_position + 1 < len(caption_indexes)
            else len(lines)
        )
        table_text = "\n".join(
            lines[caption_index:next_caption_index]
        ).strip()

        if table_text:
            separated.append({
                **block,
                "content_type": "table",
                "table_caption": lines[caption_index].strip(),
                "text": table_text,
            })

    return separated


def split_text_into_line_groups(
    text: str,
    target_chars: int = 1200,
) -> list[str]:
    """Split layout-sensitive text at extracted line boundaries."""
    lines = [line.rstrip() for line in text.splitlines()]
    groups: list[str] = []
    current_lines: list[str] = []

    for line in lines:
        candidate = "\n".join(current_lines + [line]).strip()

        if current_lines and len(candidate) > target_chars:
            group = "\n".join(current_lines).strip()
            if group:
                groups.append(group)
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        group = "\n".join(current_lines).strip()
        if group:
            groups.append(group)

    return groups


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

    Preserves all semantic-unit metadata attached before retrieval splitting.
    """
    text = block["text"]
    if len(text) <= max_chars:
        return [block]

    if block.get("content_type") == "table":
        return [
            {
                **block,
                "text": group,
            }
            for group in split_text_into_line_groups(
                text,
                target_chars=max_chars,
            )
        ]

    paragraphs = split_text_into_paragraphs(text)

    # If paragraph splitting is weak (one giant paragraph), fall back
    if len(paragraphs) <= 1:
        sentence_groups = split_text_into_sentence_groups(text, target_chars=max_chars)
        return [
            {
                **block,
                "text": group,
            }
            for group in sentence_groups
            if group.strip()
        ]

    chunks: list[dict[str, Any]] = []
    current_parts: list[str] = []

    for paragraph in paragraphs:
        paragraph_parts = [paragraph]

        if len(paragraph) > max_chars:
            paragraph_parts = split_text_into_sentence_groups(
                paragraph,
                target_chars=max_chars,
            )

        for part in paragraph_parts:
            candidate = "\n\n".join(current_parts + [part]).strip()

            if current_parts and len(candidate) > max_chars:
                chunks.append({
                    **block,
                    "text": "\n\n".join(current_parts).strip(),
                })
                current_parts = [part]
            else:
                current_parts.append(part)

    if current_parts:
        chunks.append({
            **block,
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
                **block,
                "heading": "Abstract",
                "text": text,
            }

        adjusted.append(block)

    return adjusted


def semantic_unit_grouping_key(block: dict[str, Any]) -> tuple[Any, ...] | None:
    """
    Return the structural identity used for conservative unit continuation.

    Unlabelled blocks and bare heuristic headings intentionally receive no
    grouping key. Cross-page continuation requires authoritative TOC
    provenance, a known generic heading, an explicit subheading, or an
    authoritative table caption, preventing bare table labels and damaged
    running headers from creating accidental multi-page units.
    """
    heading = normalize_heading(block.get("heading") or "")
    subheading = normalize_heading(block.get("subheading") or "")

    has_toc_provenance = block.get("section_printed_page") is not None
    has_known_heading = heading in KNOWN_HEADINGS
    has_table_caption = bool(block.get("table_caption"))

    if (
        not subheading
        and not has_toc_provenance
        and not has_known_heading
        and not has_table_caption
    ):
        return None

    return (
        block.get("major_section"),
        block.get("category"),
        block.get("section_printed_page"),
        heading,
        subheading,
        block.get("content_type", "prose"),
        normalize_heading(block.get("table_caption") or ""),
    )


def group_blocks_into_semantic_units(
    blocks: list[dict[str, Any]],
) -> list[list[dict[str, Any]]]:
    """
    Group consecutive, structurally identical blocks across contiguous pages.

    Physical page blocks remain intact inside each unit. This lets retrieval
    children retain exact, page-local source spans while their semantic parent
    can cover a naturally variable page range.
    """
    units: list[list[dict[str, Any]]] = []

    for block in blocks:
        key = semantic_unit_grouping_key(block)
        page_number = block.get("page_number")

        if units:
            previous_block = units[-1][-1]
            previous_key = semantic_unit_grouping_key(previous_block)
            previous_page = previous_block.get("page_number")
            pages_are_contiguous = (
                isinstance(page_number, int)
                and isinstance(previous_page, int)
                and previous_page <= page_number <= previous_page + 1
            )

            if (
                key is not None
                and key == previous_key
                and pages_are_contiguous
            ):
                units[-1].append(block)
                continue

        units.append([block])

    return units


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
    page_furniture = detect_repeated_page_furniture(pages)
    
    toc_entries = extract_toc_hierarchy(cleaned_text)

    toc_heading_lookup = {
        normalize_heading(entry["title"]): entry["title"]
        for entry in toc_entries
        if entry.get("title")
    }

    major_sections = extract_major_toc_sections(cleaned_text)

    toc_entries = attach_major_sections_to_toc_entries(
        toc_entries,
        major_sections,
    )

    toc_hierarchy_lookup = build_toc_hierarchy_lookup(toc_entries)
    printed_page_offset = infer_printed_page_offset(pages, toc_entries)

    raw_blocks: list[dict[str, Any]] = []
    current_heading: str | None = None
    current_subheading: str | None = None

    for page in pages:
        page_text = strip_repeated_page_furniture(
            page["text"],
            page_furniture,
        )

        if looks_like_global_contents_page(page_text):
            raw_blocks.extend(split_global_contents_page_into_blocks(
                page["page_number"],
                page_text,
            ))
            # The catalog is self-contained navigation, not a body heading
            # whose state should leak into the following page.
            current_heading = None
            current_subheading = None
            continue

        is_roman_front_matter = looks_like_roman_front_matter_page(page_text)
        if is_roman_front_matter:
            page_text = strip_roman_front_matter_page_label(page_text)

        toc_heading_candidates = toc_heading_candidates_for_page(
            toc_entries,
            page["page_number"],
            printed_page_offset,
        )
        page_blocks, current_heading, current_subheading = split_page_into_blocks(
            page["page_number"],
            page_text,
            inherited_heading=current_heading,
            inherited_subheading=current_subheading,
            toc_heading_candidates=toc_heading_candidates,
            toc_heading_lookup=toc_heading_lookup,
            allow_heuristic_headings=not is_roman_front_matter,
        )
        raw_blocks.extend(page_blocks)

    raw_blocks = apply_front_matter_rules(raw_blocks)
    table_aware_blocks: list[dict[str, Any]] = []

    for block in raw_blocks:
        table_aware_blocks.extend(split_block_at_table_captions(block))

    raw_blocks = table_aware_blocks

    structured_blocks: list[dict[str, Any]] = []
    for block in raw_blocks:
        hierarchy = resolve_toc_hierarchy(
            block["heading"],
            block["page_number"],
            toc_hierarchy_lookup,
            printed_page_offset,
        )
        section_printed_page = hierarchy.get("printed_page")
        estimated_printed_page = (
            block["page_number"] - printed_page_offset
            if printed_page_offset is not None
            else None
        )
        structured_blocks.append({
            **block,
            "major_section": hierarchy.get("major_section"),
            "category": hierarchy.get("category"),
            "printed_page": section_printed_page,
            "section_printed_page": section_printed_page,
            "estimated_printed_page": estimated_printed_page,
            "printed_page_offset": printed_page_offset,
        })

    semantic_units = group_blocks_into_semantic_units(structured_blocks)

    sized_blocks: list[dict[str, Any]] = []
    for semantic_unit_index, unit_blocks in enumerate(semantic_units, start=1):
        semantic_unit_id = f"{doc_id}_unit_{semantic_unit_index:04d}"
        semantic_unit_page_start = unit_blocks[0]["page_number"]
        semantic_unit_page_end = unit_blocks[-1]["page_number"]
        retrieval_blocks: list[dict[str, Any]] = []

        for block in unit_blocks:
            retrieval_blocks.extend(split_oversized_block(
                {
                    **block,
                    "semantic_unit_id": semantic_unit_id,
                    "semantic_unit_index": semantic_unit_index,
                },
                max_chars=max_chars,
            ))

        retrieval_chunk_count = len(retrieval_blocks)
        semantic_unit_char_count = sum(
            len(retrieval_block["text"])
            for retrieval_block in retrieval_blocks
        )

        for retrieval_chunk_index, retrieval_block in enumerate(
            retrieval_blocks,
            start=1,
        ):
            sized_blocks.append({
                **retrieval_block,
                "retrieval_chunk_index": retrieval_chunk_index,
                "retrieval_chunk_count": retrieval_chunk_count,
                "semantic_unit_page_start": semantic_unit_page_start,
                "semantic_unit_page_end": semantic_unit_page_end,
                "semantic_unit_char_count": semantic_unit_char_count,
                "semantic_unit_block_count": len(unit_blocks),
            })

    chunks: list[dict[str, Any]] = []

    current_offset = 0
    pages_by_number = {
        page["page_number"]: page
        for page in pages
    }
    page_search_cursors: dict[int, int] = {}

    for index, block in enumerate(sized_blocks, start=1):
        block_text = block["text"]

        char_start = current_offset
        char_end = current_offset + len(block_text)

        source_char_start: int | None = None
        source_char_end: int | None = None
        source_page = pages_by_number.get(block["page_number"])

        if source_page is not None:
            page_cursor = page_search_cursors.get(block["page_number"], 0)
            source_span = find_source_text_span(
                block_text,
                source_page["text"],
                start_at=page_cursor,
            )

            if source_span is not None:
                page_start, page_end = source_span
                source_char_start = source_page["source_char_start"] + page_start
                source_char_end = source_page["source_char_start"] + page_end
                page_search_cursors[block["page_number"]] = page_end

        chunks.append({
            "chunk_id": f"{doc_id}_chunk_{index:04d}",
            "doc_id": doc_id,
            "chunk_index": index,
            "semantic_unit_id": block["semantic_unit_id"],
            "semantic_unit_index": block["semantic_unit_index"],
            "semantic_unit_page_start": block["semantic_unit_page_start"],
            "semantic_unit_page_end": block["semantic_unit_page_end"],
            "semantic_unit_char_count": block["semantic_unit_char_count"],
            "semantic_unit_block_count": block["semantic_unit_block_count"],
            "retrieval_chunk_index": block["retrieval_chunk_index"],
            "retrieval_chunk_count": block["retrieval_chunk_count"],
            "page_start": block["page_number"],
            "page_end": block["page_number"],
            "section_heading": block["heading"],
            "subheading": block.get("subheading"),
            "content_type": block.get("content_type", "prose"),
            "table_caption": block.get("table_caption"),
            "major_section": block.get("major_section"),
            "category": block.get("category"),
            # Compatibility alias for pre-provenance-separation consumers.
            # This is the section's TOC start page, not the chunk's page.
            "printed_page": block.get("section_printed_page"),
            "section_printed_page": block.get("section_printed_page"),
            "estimated_printed_page": block.get("estimated_printed_page"),
            "printed_page_offset": block.get("printed_page_offset"),
            "running_header": block.get("running_header"),
            "layout_hint": equation_layout_hint(block_text),
            "text": block_text,
            "char_count": len(block_text),
            "char_start": char_start,
            "char_end": char_end,
            "source_char_start": source_char_start,
            "source_char_end": source_char_end,
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
