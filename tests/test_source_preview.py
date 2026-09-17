from pypdf import PdfWriter
import pytest

from ingestion.source_preview import render_pdf_page_preview


def test_render_pdf_page_preview_writes_png(tmp_path):
    pdf_path = tmp_path / "source.pdf"
    image_path = tmp_path / "previews" / "page_0001.png"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with pdf_path.open("wb") as pdf_file:
        writer.write(pdf_file)

    result = render_pdf_page_preview(pdf_path, 1, image_path, resolution=72)

    assert result == image_path
    assert image_path.read_bytes().startswith(b"\x89PNG")


def test_render_pdf_page_preview_rejects_out_of_range_page(tmp_path):
    pdf_path = tmp_path / "source.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with pdf_path.open("wb") as pdf_file:
        writer.write(pdf_file)

    with pytest.raises(ValueError, match="outside 1-1"):
        render_pdf_page_preview(pdf_path, 2, tmp_path / "page_0002.png")
