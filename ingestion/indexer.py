from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import re
import shutil

from ingestion.paths import NOTES_ROOT


GENERATED_ROOT = NOTES_ROOT / "_generated"


def slugify_for_filename(text: str) -> str:
    """
    Make a filesystem-safe slug for generated note filenames.
    """
    text = text.strip().lower()
    text = re.sub(r"[\s\-]+", "_", text)
    text = re.sub(r"[^a-z0-9_]", "", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "untitled"

def build_generated_note_id(doc_id: str, suffix: str) -> str:
    """
    Build a stable note_id for generated notes.
    """
    safe_suffix = slugify_for_filename(suffix)
    return f"note_{doc_id}_{safe_suffix}"

def build_generated_doc_dir(category_path: str, doc_id: str) -> Path:
    """
    Build the generated output directory for one ingested document.
    """
    category_parts = [part for part in category_path.split("/") if part]
    return GENERATED_ROOT.joinpath(*category_parts, doc_id)


def chunk_to_note_text(chunk: dict[str, Any], metadata: dict[str, Any]) -> str:
    """
    Convert one chunk + document metadata into a markdown note string.
    """
    title_base = metadata["title"].replace("_", " ").strip()
    chunk_num = f"{chunk['chunk_index']:04d}"
    note_id = build_generated_note_id(
    metadata["doc_id"],
    f"chunk_{chunk_num}"
    )
    section_heading = chunk.get("section_heading") or ""
    aliases = f"{title_base} chunk {chunk_num}"

    tags = [
        "generated",
        "ingested_pdf",
    ]
    tags.extend([part for part in metadata["category_path"].split("/") if part])

    lines = [
        f"title: {title_base} - chunk {chunk_num}",
        f"note_id: {note_id}",
        f"tags: {', '.join(tags)}",
        f"aliases: {aliases}",
        f"source_doc_id: {metadata['doc_id']}",
        f"source_filename: {metadata['source_filename']}",
        f"chunk_index: {chunk['chunk_index']}",
        f"semantic_unit_id: {chunk.get('semantic_unit_id', '')}",
        f"semantic_unit_index: {chunk.get('semantic_unit_index', '')}",
        f"retrieval_chunk_index: {chunk.get('retrieval_chunk_index', '')}",
        f"retrieval_chunk_count: {chunk.get('retrieval_chunk_count', '')}",
        f"page_start: {chunk['page_start']}",
        f"page_end: {chunk['page_end']}",
        f"section_heading: {section_heading}",
        f"char_count: {chunk['char_count']}",
        "",
        chunk["text"].strip(),
        "",
    ]

    return "\n".join(lines)


def structural_doc_note_text(metadata: dict[str, Any], preview_chars: int = 1200) -> str:
    """
    Build a single generated note for a structural-only document.
    """
    title_base = metadata["title"].replace("_", " ").strip()
    aliases = title_base
    note_id = build_generated_note_id(
    metadata["doc_id"],
    "structural_anchor"
    )

    tags = [
        "generated",
        "ingested_pdf",
        "structural_only",
    ]
    tags.extend([part for part in metadata["category_path"].split("/") if part])

    lines = [
        f"title: {title_base}",
        f"tags: {', '.join(tags)}",
        f"note_id: {note_id}",
        f"aliases: {aliases}",
        f"source_doc_id: {metadata['doc_id']}",
        f"source_filename: {metadata['source_filename']}",
        f"file_type: {metadata.get('file_type', '')}",
        f"page_count: {metadata.get('page_count', '')}",
        f"chunk_count_estimate: {metadata.get('chunk_count_estimate', '')}",
        f"chunk_storage_mode: {metadata.get('chunk_storage_mode', '')}",
        f"structural_index_file: {metadata.get('structural_index_file', '')}",
        "",
        "This document is stored in structural-only mode.",
        "",
        f"title: {title_base}",
        f"source file: {metadata.get('source_filename', '')}",
        f"pages: {metadata.get('page_count', '')}",
        f"Structural entries: {metadata.get('chunk_count_estimate', '')}",
        f"Storage mode: {metadata.get('chunk_storage_mode', '')}",
        "",
        "Persistent chunk notes were not generated.",
        "",
        "Use Structure View to browse the structural index and open transient reconstructed segments.",
        "",
    ]

    return "\n".join(lines)


def index_chunks_to_generated_notes(metadata_file: str | Path, clear_existing: bool = True) -> dict[str, Any]:
    """
    Read a document's metadata + chunks and generate markdown note files
    under notes/_generated/<category_path>/<doc_id>/.
    """
    metadata_path = Path(metadata_file)
    with metadata_path.open("r", encoding="utf-8") as f:
        metadata = json.load(f)

    chunks_file = Path(metadata["chunks_file"])
    with chunks_file.open("r", encoding="utf-8") as f:
        chunks = json.load(f)

    output_dir = build_generated_doc_dir(metadata["category_path"], metadata["doc_id"])

    if clear_existing and output_dir.exists():
        shutil.rmtree(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    written_files: list[str] = []

    title_slug = slugify_for_filename(metadata["title"])

    for chunk in chunks:
        chunk_num = f"{chunk['chunk_index']:04d}"
        filename = f"{title_slug}__chunk_{chunk_num}.md"
        output_path = output_dir / filename

        note_text = chunk_to_note_text(chunk, metadata)
        output_path.write_text(note_text, encoding="utf-8")
        written_files.append(str(output_path))

    return {
        "doc_id": metadata["doc_id"],
        "category_path": metadata["category_path"],
        "output_dir": str(output_dir),
        "note_count": len(written_files),
        "files": written_files,
    }

def index_structural_doc_to_generated_note(
    metadata_file: str | Path,
    clear_existing: bool = True,
) -> dict[str, Any]:
    """
    Create a single generated note for a structural-only document.
    """
    metadata_path = Path(metadata_file)
    with metadata_path.open("r", encoding="utf-8") as f:
        metadata = json.load(f)

    output_dir = build_generated_doc_dir(metadata["category_path"], metadata["doc_id"])

    if clear_existing and output_dir.exists():
        shutil.rmtree(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    title_slug = slugify_for_filename(metadata["title"])
    output_path = output_dir / f"{title_slug}__document.md"

    note_text = structural_doc_note_text(metadata)
    output_path.write_text(note_text, encoding="utf-8")

    return {
        "doc_id": metadata["doc_id"],
        "category_path": metadata["category_path"],
        "output_dir": str(output_dir),
        "note_count": 1,
        "files": [str(output_path)],
    }
