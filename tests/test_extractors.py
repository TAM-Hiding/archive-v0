from pypdf import PdfWriter

from ingestion.extractors import (
    _extract_pdfplumber_page_text,
    extract_text_from_pdf,
    save_extracted_text,
)


class RecordingPdfPlumberPage:
    def __init__(self, geometric_text, flow_text):
        self.geometric_text = geometric_text
        self.flow_text = flow_text
        self.calls = []

    def extract_text(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs["use_text_flow"]:
            return self.flow_text
        return self.geometric_text


def test_pdfplumber_uses_text_flow_for_explicit_toc_page():
    page = RecordingPdfPlumberPage(
        geometric_text=(
            "TABLE OF CONTENTS\n"
            "NUMBERS, FRACTIONS, AND GEOMETRY\n"
            "DECIMALS\n"
            "3 Inch Conversion 39 Arithmetic Sequences"
        ),
        flow_text=(
            "TABLE OF CONTENTS\n"
            "NUMBERS, FRACTIONS, AND\n"
            "DECIMALS\n"
            "3 Inch Conversion\n"
            "GEOMETRY\n"
            "39 Arithmetic Sequences"
        ),
    )

    result = _extract_pdfplumber_page_text(page)

    assert result == page.flow_text
    assert [call["use_text_flow"] for call in page.calls] == [False, True]


def test_pdfplumber_keeps_geometric_order_for_body_page():
    page = RecordingPdfPlumberPage(
        geometric_text="Body prose\n270 × 44\nx = --------",
        flow_text="unused flow text",
    )

    result = _extract_pdfplumber_page_text(page)

    assert result == page.geometric_text
    assert [call["use_text_flow"] for call in page.calls] == [False]


def test_extract_text_from_pdf(tmp_path):
    pdf_file = tmp_path / "sample.pdf"

    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)

    with pdf_file.open("wb") as f:
        writer.write(f)

    result = extract_text_from_pdf(pdf_file)

    assert result["success"] is True
    assert result["extractor"] == "pdfplumber"
    assert result["page_count"] == 1
    assert len(result["pages"]) == 1
    assert result["pages"][0]["page_number"] == 1
    assert "--- PAGE 1 ---" in result["text"]


def test_extract_text_from_pdf_supports_explicit_pypdf_mode(tmp_path):
    pdf_file = tmp_path / "sample.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with pdf_file.open("wb") as f:
        writer.write(f)

    result = extract_text_from_pdf(pdf_file, extractor="pypdf")

    assert result["extractor"] == "pypdf"
    assert result["page_count"] == 1


def test_save_extracted_text(tmp_path):
    output_file = tmp_path / "nested" / "extracted.txt"
    text = "Archive test text."

    result = save_extracted_text(output_file, text)

    assert result == output_file
    assert output_file.exists()
    assert output_file.read_text(encoding="utf-8") == text
