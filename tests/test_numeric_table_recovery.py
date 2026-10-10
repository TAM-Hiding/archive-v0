import json
from types import SimpleNamespace

from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

import archive
from app import app
from ingestion.table_layout import extract_pdf_table_layouts, recover_packed_numeric_rows


def make_numeric_table_pdf(path):
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                             NameObject("/Subtype"): NameObject("/Type1"),
                             NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"):
        DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
    ops = ["0.5 w", "BT /F1 12 Tf 100 650 Td (Conversion Table for 1 to 100) Tj ET"]
    grid = [["Offset", "0", "100"], ["1", "P", "3"], ["3", "3", "P"],
            ["5", "5", "5"], ["7", "P", "7"], ["9", "3", "3"], ["11", "P", "P"]]
    for col in range(3):
        x = 100 + col * 50
        ops += [f"{x} 600 50 30 re S", f"{x} 400 50 200 re S"]
        for row, values in enumerate(grid):
            y = 610 if row == 0 else 600 - row * 25
            ops.append(f"BT /F1 12 Tf {x + 8} {y} Td ({values[col]}) Tj ET")
    stream = DecodedStreamObject()
    stream.set_data("\n".join(ops).encode())
    page[NameObject("/Contents")] = writer._add_object(stream)
    writer.write(path)
    return grid


def test_numeric_recovery_and_exact_cell_api_keep_provenance(tmp_path, monkeypatch):
    path = tmp_path / "source.pdf"
    expected = make_numeric_table_pdf(path)
    layouts = extract_pdf_table_layouts(path, [1])
    assert len(layouts) == 1
    layout = layouts[0]
    assert layout["grid"] == expected
    assert len(layout["ruled_grid"]) == 2
    assert len(layout["cells"]) == 21
    assert all(cell["bbox"] and cell["source_cell_bbox"] for cell in layout["cells"])
    manifest = tmp_path / "tables.json"
    manifest.write_text(json.dumps({"layouts": layouts}))
    monkeypatch.setattr(archive, "get_ingested_document", lambda _: {
        "doc_id": "doc", "table_layout_file": str(manifest)})
    client = app.test_client()
    response = client.get("/api/document/doc/table/page_0001_table_01/cell/2/3")
    assert response.status_code == 200
    assert response.json["value"] == "3"
    assert response.json["row"] == 2 and response.json["column"] == 3
    assert response.json["cell_bbox"] and response.json["page_number"] == 1
    assert client.get("/api/document/doc/table/page_0001_table_01/cell/0/1").status_code == 400
    assert client.get("/api/document/doc/table/page_0001_table_01/cell/20/1").status_code == 404
    assert client.get("/api/document/doc/table/not-in-manifest/cell/1/1").status_code == 404


def test_recovery_refuses_incomplete_cells_and_wrapped_prose():
    boxes = [(0, 0, 10, 100), (10, 0, 20, 100), (20, 0, 30, 100)]
    table = SimpleNamespace(rows=[SimpleNamespace(cells=boxes)])
    words = [{"text": "3", "x0": col * 10 + 1, "x1": col * 10 + 5,
              "top": row * 10, "bottom": row * 10 + 5}
             for row in range(6) for col in range(3)]

    class Page:
        def crop(self, bbox):
            return self

        def extract_words(self, **kwargs):
            return words

    assert recover_packed_numeric_rows(Page(), table, [["3\n3"] * 3]) is not None
    words.pop()
    assert recover_packed_numeric_rows(Page(), table, [["3\n3"] * 3]) is None
    words.append({"text": "prose", "x0": 21, "x1": 25, "top": 50, "bottom": 55})
    assert recover_packed_numeric_rows(Page(), table, [["3\n3"] * 3]) is None
