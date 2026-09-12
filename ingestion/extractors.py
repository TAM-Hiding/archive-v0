from __future__ import annotations

from pathlib import Path
from typing import Any

from pypdf import PdfReader


def _build_extraction_result(
    pages_output: list[dict[str, Any]],
    extractor: str,
) -> dict[str, Any]:
    full_text_parts: list[str] = []
    for page in pages_output:
        full_text_parts.append(f"\n--- PAGE {page['page_number']} ---\n")
        full_text_parts.append(page["text"])

    return {
        "success": True,
        "page_count": len(pages_output),
        "text": "\n".join(full_text_parts).strip(),
        "pages": pages_output,
        "extractor": extractor,
    }


def extract_text_from_pdf(
    pdf_path: str | Path,
    extractor: str = "pdfplumber",
) -> dict[str, Any]:
    """
    Extract text from a text-based PDF.

    pdfplumber is the default because it reconstructs visible geometric order,
    keeping displayed equations near the prose that introduces them. pypdf is
    retained as an explicit compatibility option.

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

    if extractor not in {"pdfplumber", "pypdf"}:
        raise ValueError(
            f"Unsupported PDF extractor {extractor!r}; "
            "expected 'pdfplumber' or 'pypdf'"
        )

    pages_output: list[dict[str, Any]] = []

    if extractor == "pdfplumber":
        import pdfplumber

        with pdfplumber.open(pdf_file) as pdf:
            for index, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text(
                    x_tolerance=1,
                    y_tolerance=3,
                    use_text_flow=False,
                ) or ""
                pages_output.append({
                    "page_number": index,
                    "text": page_text.strip(),
                })
    else:
        reader = PdfReader(str(pdf_file))
        for index, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            pages_output.append({
                "page_number": index,
                "text": page_text.strip(),
            })

    return _build_extraction_result(pages_output, extractor)


def save_extracted_text(output_path: str | Path, text: str) -> Path:
    """
    Save extracted text to disk as UTF-8.
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8") as f:
        f.write(text)

    return output_file
