from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Iterable

from ingestion.table_layout import group_words_into_positioned_lines


FIGURE_CAPTION_PATTERN = re.compile(
    r"^Fig(?:ure)?\.?\s*\d+[A-Za-z]?(?:[.:\-–—]|\s)",
    re.IGNORECASE,
)


def normalize_figure_caption(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def find_figure_candidate_pages(cleaned_text: str) -> set[int]:
    """Find physical pages containing a caption-looking line."""
    from ingestion.chunkers import parse_cleaned_text_into_pages

    return {
        int(page["page_number"])
        for page in parse_cleaned_text_into_pages(cleaned_text)
        if any(
            FIGURE_CAPTION_PATTERN.match(line.strip())
            for line in page["text"].splitlines()
        )
    }


def parse_page_spec(value: str) -> set[int]:
    """Parse a one-based page list such as ``754,760-762``."""
    pages: set[int] = set()
    for part in value.split(","):
        item = part.strip()
        if not item:
            continue
        if "-" in item:
            start_text, end_text = item.split("-", 1)
            start = int(start_text)
            end = int(end_text)
            if end < start:
                raise ValueError(f"Invalid descending page range: {item}")
            pages.update(range(start, end + 1))
        else:
            pages.add(int(item))
    if any(page < 1 for page in pages):
        raise ValueError("PDF page numbers must be positive")
    return pages


def _object_bbox(item: dict[str, Any]) -> tuple[float, float, float, float] | None:
    values = (item.get("x0"), item.get("top"), item.get("x1"), item.get("bottom"))
    if any(value is None for value in values):
        return None
    return tuple(float(value) for value in values)


def extract_page_figure_layouts(
    page: Any,
    page_number: int,
) -> list[dict[str, Any]]:
    """Locate caption-led raster or vector figure regions on one PDF page."""
    words = page.extract_words(
        x_tolerance=2,
        y_tolerance=2,
        keep_blank_chars=False,
        use_text_flow=False,
    )
    positioned_lines = group_words_into_positioned_lines(words)
    caption_lines = [
        line for line in positioned_lines
        if FIGURE_CAPTION_PATTERN.match(line.get("text", "").strip())
    ]

    graphic_objects = [
        item
        for item in (
            list(page.images)
            + list(page.lines)
            + list(page.rects)
            + list(page.curves)
        )
        if _object_bbox(item) is not None
    ]
    layouts: list[dict[str, Any]] = []
    previous_caption_bottom = float(page.bbox[1])

    for figure_index, caption_line in enumerate(caption_lines, start=1):
        caption_top = float(caption_line["top"])
        caption_bottom = float(caption_line["bottom"])
        candidates = []
        for item in graphic_objects:
            bbox = _object_bbox(item)
            if bbox is None:
                continue
            _, top, _, bottom = bbox
            if top >= previous_caption_bottom - 1 and bottom <= caption_top + 1:
                candidates.append(item)

        previous_caption_bottom = caption_bottom
        if not candidates:
            continue

        bboxes = [_object_bbox(item) for item in candidates]
        valid_bboxes = [bbox for bbox in bboxes if bbox is not None]
        graphic_top = min(bbox[1] for bbox in valid_bboxes)
        graphic_x0 = min(bbox[0] for bbox in valid_bboxes)
        graphic_x1 = max(bbox[2] for bbox in valid_bboxes)
        caption_x0 = min(token[0] for token in caption_line["tokens"])
        caption_x1 = max(token[1] for token in caption_line["tokens"])

        nearby_words = [
            word for word in words
            if float(word["top"]) >= graphic_top - 2
            and float(word["bottom"]) <= caption_bottom + 1
        ]
        word_x0 = min(
            (float(word["x0"]) for word in nearby_words),
            default=graphic_x0,
        )
        word_x1 = max(
            (float(word["x1"]) for word in nearby_words),
            default=graphic_x1,
        )

        page_x0, page_top, page_x1, page_bottom = map(float, page.bbox)
        crop_bbox = [
            round(max(page_x0, min(graphic_x0, caption_x0, word_x0) - 10), 3),
            round(max(page_top, graphic_top - 8), 3),
            round(min(page_x1, max(graphic_x1, caption_x1, word_x1) + 10), 3),
            round(min(page_bottom, caption_bottom + 5), 3),
        ]
        crop_text = page.crop(tuple(crop_bbox)).extract_text(
            x_tolerance=2,
            y_tolerance=2,
            use_text_flow=False,
        ) or ""
        layout_id = f"page_{page_number:04d}_figure_{figure_index:02d}"
        layouts.append({
            "layout_id": layout_id,
            "page_number": page_number,
            "figure_index": figure_index,
            "caption": caption_line["text"].strip(),
            "caption_key": normalize_figure_caption(caption_line["text"]),
            "bbox": crop_bbox,
            "label_text": crop_text.strip(),
            "vector_object_count": sum(
                1 for item in candidates
                if item.get("object_type") in {"line", "rect", "curve"}
            ),
            "embedded_image_count": sum(
                1 for item in candidates if item.get("object_type") == "image"
            ),
        })

    return layouts


def extract_pdf_figure_layouts(
    pdf_path: str | Path,
    output_directory: str | Path,
    page_numbers: Iterable[int],
    resolution: int = 160,
) -> list[dict[str, Any]]:
    """Detect and render caption-led figure groups from selected PDF pages."""
    import pdfplumber

    pdf_file = Path(pdf_path).expanduser().resolve()
    if not pdf_file.is_file():
        raise FileNotFoundError(f"PDF file not found: {pdf_file}")
    output_root = Path(output_directory)
    output_root.mkdir(parents=True, exist_ok=True)

    layouts: list[dict[str, Any]] = []
    pdfminer_logger = logging.getLogger("pdfminer.pdfinterp")
    previous_log_level = pdfminer_logger.level
    pdfminer_logger.setLevel(logging.ERROR)
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page_number in sorted(set(int(number) for number in page_numbers)):
                if page_number < 1 or page_number > len(pdf.pages):
                    raise ValueError(
                        f"PDF page {page_number} is outside 1-{len(pdf.pages)}"
                    )
                page = pdf.pages[page_number - 1]
                page_layouts = extract_page_figure_layouts(page, page_number)
                for layout in page_layouts:
                    image_name = f"{layout['layout_id']}.png"
                    image_path = output_root / image_name
                    page.crop(tuple(layout["bbox"])).to_image(
                        resolution=resolution,
                        antialias=True,
                    ).save(image_path)
                    layout["image_filename"] = image_name
                    layouts.append(layout)
    finally:
        pdfminer_logger.setLevel(previous_log_level)

    return layouts


def write_figure_manifest(
    manifest_path: str | Path,
    doc_id: str,
    source_filename: str,
    layouts: list[dict[str, Any]],
) -> dict[str, Any]:
    path = Path(manifest_path)
    records = []
    for layout in layouts:
        records.append({
            **layout,
            "file": str(Path("figure_layouts") / layout["image_filename"]),
        })
    payload = {
        "schema_version": 1,
        "storage_mode": "image_shards",
        "doc_id": doc_id,
        "source_filename": source_filename,
        "figure_count": len(records),
        "figures": records,
    }
    temporary_path = path.with_name(f".{path.name}.tmp")
    temporary_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary_path.replace(path)
    return payload
