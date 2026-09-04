from pypdf import PdfWriter

from ingestion.extractors import extract_text_from_pdf, save_extracted_text


def test_extract_text_from_pdf(tmp_path):
    pdf_file = tmp_path / "sample.pdf"

    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)

    with pdf_file.open("wb") as f:
        writer.write(f)

    result = extract_text_from_pdf(pdf_file)

    assert result["success"] is True
    assert result["extractor"] == "pypdf"
    assert result["page_count"] == 1
    assert len(result["pages"]) == 1
    assert result["pages"][0]["page_number"] == 1
    assert "--- PAGE 1 ---" in result["text"]


def test_save_extracted_text(tmp_path):
    output_file = tmp_path / "nested" / "extracted.txt"
    text = "Archive test text."

    result = save_extracted_text(output_file, text)

    assert result == output_file
    assert output_file.exists()
    assert output_file.read_text(encoding="utf-8") == text
