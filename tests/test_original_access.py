import json

from flask import render_template
from pypdf import PdfWriter
import pytest

import archive
from app import app


@pytest.fixture
def source_document(tmp_path, monkeypatch):
    folder = tmp_path / "documents" / "doc"
    folder.mkdir(parents=True)
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=400)
    writer.add_blank_page(width=300, height=400)
    source = folder / "source.pdf"
    writer.write(source)
    metadata = {"doc_id": "doc", "title": "Example", "source_filename": "example.pdf",
                "stored_source_filename": "source.pdf", "doc_root": str(folder)}
    (folder / "metadata.json").write_text(json.dumps(metadata))
    monkeypatch.setattr(archive, "archive_documents_path", str(folder.parent))
    return folder, source


def test_original_route_returns_unchanged_pdf_inline(source_document):
    folder, source = source_document
    before = source.read_bytes()
    document = archive.get_ingested_document("doc")
    assert document["has_source_pdf"]
    response = app.test_client().get("/curator/document/doc/original")
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.headers["Content-Disposition"].startswith("inline;")
    assert response.data == before
    assert source.read_bytes() == before


def test_original_controls_are_available_for_prose(source_document, monkeypatch):
    _, _ = source_document
    document = archive.get_ingested_document("doc")
    entry = {"entry_index": 0, "chunk_index": 0, "page_start": 2, "page_end": 2,
             "char_count": 23, "preview": "Ordinary prose content.", "content_type": "prose"}
    monkeypatch.setattr(archive, "get_structural_index_for_document",
                        lambda _: {"document": document, "entries": [entry]})
    segment = archive.get_structural_segment("doc", 0)
    assert segment["source_verification_pages"] == [2]
    assert not segment["source_verification_open"]
    with app.test_request_context("/"):
        card = render_template("partials/structural_entry_card.html",
                               entry=entry, document={"document": document})
        context = render_template("structural_segment.html", segment=segment)
    for html in [card, context]:
        assert 'href="/curator/document/doc/original#page=2"' in html
        assert "View original" in html
    assert "Original PDF pages" in context
    assert 'id="source-page-2"' in context


def test_long_prose_unit_previews_requested_entry(monkeypatch):
    entries = [{"page_start": i, "page_end": i, "preview": "Prose",
                "semantic_unit_id": "long-unit", "content_type": "prose"}
               for i in range(1, 21)]
    monkeypatch.setattr(archive, "get_structural_index_for_document", lambda _: {
        "document": {"doc_id": "doc", "title": "Example", "has_source_pdf": True},
        "entries": entries})
    segment = archive.get_structural_segment("doc", 19)
    assert segment["source_verification_pages"] == [20]


@pytest.mark.parametrize("filename", ["../outside.pdf", "not-pdf.txt", "missing.pdf"])
def test_original_source_rejects_missing_or_untrusted_paths(source_document, filename):
    folder, _ = source_document
    metadata_file = folder / "metadata.json"
    metadata = json.loads(metadata_file.read_text())
    metadata["stored_source_filename"] = filename
    metadata_file.write_text(json.dumps(metadata))
    assert not archive.get_ingested_document("doc")["has_source_pdf"]
    assert app.test_client().get("/curator/document/doc/original").status_code == 404


def test_original_source_rejects_symlink_outside_document(source_document, tmp_path):
    folder, source = source_document
    outside = tmp_path / "outside.pdf"
    source.rename(outside)
    source.symlink_to(outside)
    assert archive.get_original_pdf_path("doc") is None
    assert archive.get_original_pdf_path("../doc") is None


def test_missing_source_hides_original_link(source_document):
    _, source = source_document
    source.unlink()
    document = archive.get_ingested_document("doc")
    with app.test_request_context("/"):
        html = render_template("curator_document.html", document=document)
    assert "View original" not in html
