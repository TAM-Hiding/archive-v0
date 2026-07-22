from __future__ import annotations

from pathlib import Path
from datetime import datetime
import json
import shutil

from ingestion.paths import normalize_path, ensure_category_path_exists, NOTES_ROOT


ARCHIVE_DATA_ROOT = NOTES_ROOT / "_archive_data"
DOCUMENTS_ROOT = ARCHIVE_DATA_ROOT / "documents"


def ensure_archive_data_dirs() -> None:
    """
    Ensure internal archive data directories exist.
    """
    DOCUMENTS_ROOT.mkdir(parents=True, exist_ok=True)


def generate_doc_id() -> str:
    """
    Generate a simple timestamp-based document ID.

    Example:
        20260408_101530_123456
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def guess_file_type(file_path: Path) -> str:
    """
    Guess file type from file suffix.
    """
    suffix = file_path.suffix.lower().lstrip(".")
    return suffix if suffix else "unknown"


def build_document_paths(doc_id: str) -> dict[str, Path]:
    """
    Build the canonical storage paths for a document.
    """
    doc_root = DOCUMENTS_ROOT / doc_id
    return {
        "doc_root": doc_root,
        "source_file": doc_root / "source",
        "metadata_file": doc_root / "metadata.json",
        "extracted_text_file": doc_root / "extracted_text.txt",
        "chunks_file": doc_root / "chunks.json",
    }


def create_document_record(source_file_path: str | Path, category_path: str) -> dict:
    """
    Register a source document in the archive system.

    Steps:
    - normalize and ensure the category path exists
    - create an internal document storage folder
    - copy the source file into that folder
    - create metadata.json

    Returns the metadata dictionary.
    """
    ensure_archive_data_dirs()

    source_path = Path(source_file_path).expanduser().resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    if not source_path.is_file():
        raise ValueError(f"Source path is not a file: {source_path}")

    normalized_category_path = normalize_path(category_path)
    ensure_category_path_exists(NOTES_ROOT, normalized_category_path)

    doc_id = generate_doc_id()
    doc_paths = build_document_paths(doc_id)
    doc_root = doc_paths["doc_root"]
    doc_root.mkdir(parents=True, exist_ok=False)

    file_type = guess_file_type(source_path)
    copied_source_path = doc_paths["source_file"].with_suffix(source_path.suffix.lower())

    shutil.copy2(source_path, copied_source_path)

    metadata = {
        "doc_id": doc_id,
        "title": source_path.stem,
        "source_filename": source_path.name,
        "stored_source_filename": copied_source_path.name,
        "source_original_path": str(source_path),
        "category_path": normalized_category_path,
        "file_type": file_type,
        "status": "registered",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "doc_root": str(doc_root),
        "metadata_file": str(doc_paths["metadata_file"]),
        "extracted_text_file": str(doc_paths["extracted_text_file"]),
        "chunks_file": str(doc_paths["chunks_file"]),
    }

    write_metadata(doc_paths["metadata_file"], metadata)
    return metadata


def write_metadata(metadata_file: str | Path, metadata: dict) -> None:
    """
    Write metadata dict to JSON.
    """
    metadata_path = Path(metadata_file)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)

    with metadata_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


def read_metadata(metadata_file: str | Path) -> dict:
    """
    Read metadata JSON from disk.
    """
    metadata_path = Path(metadata_file)
    with metadata_path.open("r", encoding="utf-8") as f:
        return json.load(f)
