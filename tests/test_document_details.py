import json
from pathlib import Path

import pytest
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

import archive
from app import app
from ingestion.document_names import suggest_document_title


@pytest.fixture
def stored_document(tmp_path, monkeypatch):
    notes = tmp_path / "notes"
    documents = notes / "_archive_data" / "documents"
    folder = documents / "doc_001"
    folder.mkdir(parents=True)
    source = folder / "source.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_metadata({"/Title": "Machinery's Handbook — 30th Edition"})
    writer.write(source)
    metadata = {"doc_id": "doc_001", "title": "machinery-1",
                "source_filename": "machinery-1.pdf",
                "stored_source_filename": "source.pdf",
                "chunk_storage_mode": "structural_only", "status": "chunked"}
    (folder / "metadata.json").write_text(json.dumps(metadata))
    monkeypatch.setattr(archive, "archive_documents_path", str(documents))
    monkeypatch.setattr(archive, "generated_notes_path", str(notes / "_generated"))
    monkeypatch.setattr(archive, "notes_path", str(notes))
    return folder, metadata


def test_rename_preserves_source_and_note_identity_and_updates_search(stored_document):
    folder, metadata = stored_document
    source_before = (folder / "source.pdf").read_bytes()
    note_folder = folder.parents[2] / "_generated"
    note_folder.mkdir()
    note = note_folder / "old-name.md"
    content = "title: machinery-1\nnote_id: stable-id\nsource_doc_id: doc_001\n\nOriginal text"
    note.write_text(content)
    client = app.test_client()
    response = client.post("/curator/document/doc_001/details", data={
        "title": "Machinery's Handbook — 30th Edition", "collection": "private"})
    assert response.status_code == 302
    saved = json.loads((folder / "metadata.json").read_text())
    assert saved["source_filename"] == metadata["source_filename"]
    assert saved["doc_id"] == "doc_001"
    assert (folder / "source.pdf").read_bytes() == source_before
    assert note.read_text() == content
    loaded = archive.load_notes()[0]
    assert loaded["meta"]["note_id"] == "stable-id"
    assert "30th edition" in loaded["title_search"]
    assert "machinery-1" in loaded["aliases"]
    general = client.get("/curator/documents").get_data(as_text=True)
    private = client.get("/curator/documents?view=private").get_data(as_text=True)
    public = client.get("/curator/documents?view=public").get_data(as_text=True)
    assert "30th Edition" in general and "30th Edition" in private
    assert "30th Edition" not in public


@pytest.mark.parametrize("title,collection", [("", "general"), ("bad\nname", "public"),
                                               ("Valid", "unknown"), ("x" * 301, "private")])
def test_invalid_details_leave_metadata_unchanged(stored_document, title, collection):
    folder, _ = stored_document
    before = (folder / "metadata.json").read_bytes()
    response = app.test_client().post("/curator/document/doc_001/details",
                                     data={"title": title, "collection": collection})
    assert response.status_code == 400
    assert (folder / "metadata.json").read_bytes() == before


def test_suggestion_is_reviewable_and_does_not_save(stored_document):
    folder, _ = stored_document
    before = (folder / "metadata.json").read_bytes()
    response = app.test_client().post("/curator/document/doc_001/suggest-name")
    assert response.status_code == 200
    assert "30th Edition" in response.get_data(as_text=True)
    assert (folder / "metadata.json").read_bytes() == before


def test_missing_document_details():
    assert app.test_client().post("/curator/document/missing/details").status_code == 404


def test_title_page_detects_title_and_edition_without_metadata(tmp_path):
    source = tmp_path / "machinery-1.pdf"
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                             NameObject("/Subtype"): NameObject("/Type1"),
                             NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"):
        DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 32 Tf 50 650 Td (Machinery's Handbook) Tj ET\n"
                    b"BT /F1 16 Tf 50 610 Td (30th Edition) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    writer.write(source)
    suggestion = suggest_document_title(source)
    assert suggestion["title"].replace("’", "'") == "Machinery's Handbook — 30th Edition"
    assert suggestion["source"] == "Opening page 1"


def test_blank_and_invalid_pdf_have_no_suggestion(tmp_path):
    source = tmp_path / "blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_metadata({"/Title": "Untitled"})
    writer.write(source)
    assert suggest_document_title(source) is None
    source.write_bytes(b"not a PDF")
    assert suggest_document_title(source) is None
