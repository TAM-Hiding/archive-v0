from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable


TABLE_CAPTION_SEARCH_PATTERN = re.compile(
    r"\bTable\s+\d+[A-Za-z]?(?:[.:-]|\s)",
    re.IGNORECASE,
)


def normalize_table_caption(value: str) -> str:
    """Return a comparison key for captions from different extractors."""
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def _rounded_bbox(bbox: Iterable[float]) -> list[float]:
    return [round(float(value), 3) for value in bbox]


def _bbox_contains(outer: Iterable[float], inner: Iterable[float]) -> bool:
    outer_x0, outer_top, outer_x1, outer_bottom = outer
    inner_x0, inner_top, inner_x1, inner_bottom = inner
    return (
        outer_x0 <= inner_x0
        and outer_top <= inner_top
        and outer_x1 >= inner_x1
        and outer_bottom >= inner_bottom
    )


def discard_nested_tables(tables: list[Any]) -> list[Any]:
    """Remove diagram-internal grids already enclosed by a larger table."""
    retained: list[Any] = []

    for candidate in tables:
        if any(
            other is not candidate
            and other.bbox != candidate.bbox
            and _bbox_contains(other.bbox, candidate.bbox)
            for other in tables
        ):
            continue
        retained.append(candidate)

    return retained


def extract_caption_above_table(page: Any, bbox: Iterable[float]) -> str:
    """Extract the final caption-looking line immediately above a table."""
    x0, top, x1, _ = bbox
    region = page.crop((x0, max(0, top - 42), x1, top))
    text = region.extract_text(x_tolerance=2, y_tolerance=3) or ""
    flattened = " ".join(line.strip() for line in text.splitlines() if line.strip())
    matches = list(TABLE_CAPTION_SEARCH_PATTERN.finditer(flattened))

    if not matches:
        return ""

    return flattened[matches[-1].start():].strip()


def group_words_into_positioned_lines(
    words: list[dict[str, Any]],
    y_tolerance: float = 2.0,
) -> list[dict[str, Any]]:
    """Group PDF words by baseline while preserving horizontal positions."""
    ordered = sorted(
        words,
        key=lambda word: (float(word["top"]), float(word["x0"])),
    )
    groups: list[list[dict[str, Any]]] = []

    for word in ordered:
        if not groups:
            groups.append([word])
            continue

        group_top = sum(float(item["top"]) for item in groups[-1]) / len(groups[-1])
        if abs(float(word["top"]) - group_top) <= y_tolerance:
            groups[-1].append(word)
        else:
            groups.append([word])

    lines: list[dict[str, Any]] = []
    for group in groups:
        group.sort(key=lambda word: float(word["x0"]))
        tokens = [
            [
                round(float(word["x0"]), 3),
                round(float(word["x1"]), 3),
                str(word["text"]),
            ]
            for word in group
        ]
        lines.append({
            "top": round(min(float(word["top"]) for word in group), 3),
            "bottom": round(max(float(word["bottom"]) for word in group), 3),
            "text": " ".join(str(word["text"]) for word in group),
            "tokens": tokens,
        })

    return lines


def extract_page_table_layouts(page: Any, page_number: int) -> list[dict[str, Any]]:
    """Extract non-nested ruled tables and positional text from one PDF page."""
    tables = discard_nested_tables(page.find_tables())
    layouts: list[dict[str, Any]] = []

    for table_index, table in enumerate(tables, start=1):
        bbox = table.bbox
        caption = extract_caption_above_table(page, bbox)
        words = page.crop(bbox).extract_words(
            x_tolerance=2,
            y_tolerance=2,
            keep_blank_chars=False,
            use_text_flow=False,
        )
        positioned_lines = group_words_into_positioned_lines(words)

        cells: list[dict[str, Any]] = []
        for cell_index, cell_bbox in enumerate(table.cells, start=1):
            cell_text = page.crop(cell_bbox).extract_text(
                x_tolerance=2,
                y_tolerance=3,
            ) or ""
            cells.append({
                "cell_index": cell_index,
                "bbox": _rounded_bbox(cell_bbox),
                "text": cell_text.strip(),
            })

        grid = table.extract(x_tolerance=2, y_tolerance=3)

        layout_id = f"page_{page_number:04d}_table_{table_index:02d}"
        layouts.append({
            "layout_id": layout_id,
            "page_number": page_number,
            "table_index": table_index,
            "caption": caption,
            "caption_key": normalize_table_caption(caption),
            "bbox": _rounded_bbox(bbox),
            "row_count": len(grid),
            "column_count": max((len(row) for row in grid), default=0),
            "grid": grid,
            "cells": cells,
            "positioned_lines": positioned_lines,
            "reading_order_text": "\n".join(
                line["text"] for line in positioned_lines if line["text"].strip()
            ),
        })

    return layouts


def extract_pdf_table_layouts(
    pdf_path: str | Path,
    page_numbers: Iterable[int] | None = None,
) -> list[dict[str, Any]]:
    """Extract table geometry from selected one-based PDF page numbers."""
    import pdfplumber

    pdf_file = Path(pdf_path).expanduser().resolve()
    if not pdf_file.is_file():
        raise FileNotFoundError(f"PDF file not found: {pdf_file}")

    with pdfplumber.open(pdf_file) as pdf:
        if page_numbers is None:
            selected_pages = range(1, len(pdf.pages) + 1)
        else:
            selected_pages = sorted(set(int(number) for number in page_numbers))

        layouts: list[dict[str, Any]] = []
        for page_number in selected_pages:
            if page_number < 1 or page_number > len(pdf.pages):
                raise ValueError(
                    f"PDF page {page_number} is outside 1-{len(pdf.pages)}"
                )
            layouts.extend(
                extract_page_table_layouts(pdf.pages[page_number - 1], page_number)
            )

    return layouts


def match_layout_to_caption(
    layouts: list[dict[str, Any]],
    page_number: int,
    caption: str,
) -> dict[str, Any] | None:
    """Find a same-page geometry record matching an Archive table caption."""
    caption_key = normalize_table_caption(caption)
    candidates = [
        layout
        for layout in layouts
        if layout.get("page_number") == page_number
    ]

    for layout in candidates:
        layout_key = layout.get("caption_key", "")
        if caption_key and layout_key and (
            caption_key in layout_key or layout_key in caption_key
        ):
            return layout

    if len(candidates) == 1:
        return candidates[0]

    return None
