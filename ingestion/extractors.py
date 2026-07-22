from __future__ import annotations

from pathlib import Path
from typing import Any

from pypdf import PdfReader


def extract_text_from_pdf(pdf_path: str | Path) -> dict[str, Any]:
    """
    Extract text from a text-based PDF using pypdf.

    Returns a dictionary with:
    - success: bool
    - page_count: int
    - text: str
    - pages: list[dict] with page_number and text
    - extractor: str
    """
    pdf_file = Path(pdf_path).expanduser().resolve()

    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_file}")

    if not pdf_file.is_file():
        raise ValueError(f"PDF path is not a file: {pdf_file}")

    reader = PdfReader(str(pdf_file))
    pages_output: list[dict[str, Any]] = []
    full_text_parts: list[str] = []

    for index, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        page_text = page_text.strip()

        pages_output.append({
            "page_number": index,
            "text": page_text,
        })

        full_text_parts.append(f"\n--- PAGE {index} ---\n")
        full_text_parts.append(page_text)

    full_text = "\n".join(full_text_parts).strip()

    return {
        "success": True,
        "page_count": len(reader.pages),
        "text": full_text,
        "pages": pages_output,
        "extractor": "pypdf",
    }


def save_extracted_text(output_path: str | Path, text: str) -> Path:
    """
    Save extracted text to disk as UTF-8.
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8") as f:
        f.write(text)

    return output_file
