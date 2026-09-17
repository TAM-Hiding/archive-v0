from __future__ import annotations

import logging
from pathlib import Path


class SourcePreviewError(RuntimeError):
    """Raised when a valid source request cannot be rendered."""


def render_pdf_page_preview(
    pdf_path: str | Path,
    page_number: int,
    output_path: str | Path,
    resolution: int = 144,
) -> Path:
    """Render one one-based PDF page to a PNG using the original source."""
    import pdfplumber

    source_path = Path(pdf_path).expanduser().resolve()
    destination = Path(output_path)

    if not source_path.is_file():
        raise FileNotFoundError(f"PDF file not found: {source_path}")
    if page_number < 1:
        raise ValueError("PDF page numbers must be positive")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = destination.with_name(f".{destination.stem}.tmp.png")

    pdfminer_logger = logging.getLogger("pdfminer.pdfinterp")
    previous_log_level = pdfminer_logger.level
    pdfminer_logger.setLevel(logging.ERROR)
    try:
        try:
            with pdfplumber.open(source_path) as pdf:
                if page_number > len(pdf.pages):
                    raise ValueError(
                        f"PDF page {page_number} is outside 1-{len(pdf.pages)}"
                    )
                pdf.pages[page_number - 1].to_image(
                    resolution=resolution,
                    antialias=True,
                ).save(temporary_path)
            temporary_path.replace(destination)
        except (FileNotFoundError, ValueError):
            raise
        except Exception as exc:
            raise SourcePreviewError(
                f"Could not render PDF page {page_number}: {exc}"
            ) from exc
    finally:
        pdfminer_logger.setLevel(previous_log_level)
        if temporary_path.exists():
            temporary_path.unlink()

    return destination
