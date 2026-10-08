"""Conservative, local PDF title suggestions; never rename source files."""
from pathlib import Path
import re


def clean_title(value):
    title = " ".join(str(value or "").split()).strip()
    if not 3 <= len(title) <= 300 or not any(c.isalpha() for c in title):
        return None
    if title.casefold() in {"untitled", "document", "title", "table of contents", "contents"}:
        return None
    if re.search(r"\.(pdf|docx?)$", title, re.I):
        return None
    return title


def suggest_document_title(source_path):
    """Inspect metadata, then prominent text on the first five PDF pages.

    This is a suggestion, not semantic certainty. Scans without a text layer
    fall back to their filename; OCR and model inference are not required.
    """
    if Path(source_path).suffix.lower() != ".pdf":
        return None
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(source_path))
        title = clean_title((reader.metadata or {}).get("/Title"))
        if title:
            return {"title": title, "source": "PDF metadata"}
    except Exception:
        pass
    try:
        import pdfplumber
        with pdfplumber.open(source_path) as pdf:
            for page in pdf.pages[:5]:
                words = page.extract_words(extra_attrs=["size"])
                words = [w for w in words if any(c.isalpha() for c in w["text"])]
                if not words:
                    continue
                largest = max(float(w["size"]) for w in words)
                prominent = [w for w in words if float(w["size"]) >= largest * 0.85]
                prominent.sort(key=lambda w: (round(w["top"] / 5), w["x0"]))
                title = clean_title(" ".join(w["text"] for w in prominent))
                if not title or len(title) > 180 or largest < 14:
                    continue
                text = page.extract_text() or ""
                edition = re.search(r"\b(?:\d+(?:st|nd|rd|th)?|[A-Za-z-]+)\s+edition\b", text, re.I)
                if edition and edition.group().casefold() not in title.casefold():
                    title += " — " + edition.group()
                return {"title": title, "source": f"Opening page {page.page_number}"}
    except Exception:
        pass
    return None
