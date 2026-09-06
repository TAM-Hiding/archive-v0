from __future__ import annotations

from pathlib import Path
from typing import Any
import json


def build_structural_index(chunks: list[dict[str, Any]], preview_chars: int = 220) -> list[dict[str, Any]]:
    """
    Build a lightweight structural index from chunk data.

    This is intended to support long-document navigation and future
    transient chunk generation without requiring every chunk to exist
    as a persistent generated note.
    """
    index_entries: list[dict[str, Any]] = []

    for entry_index, chunk in enumerate(chunks):
        text = chunk.get("text", "").strip()
        preview = text[:preview_chars]

        if len(text) > preview_chars:
            preview += "..."

        index_entries.append({
            "entry_index": entry_index,
            "chunk_index": chunk.get("chunk_index"),
            "page_start": chunk.get("page_start"),
            "page_end": chunk.get("page_end"),
            "section_heading": chunk.get("section_heading") or "",
            "subheading": chunk.get("subheading") or "",
            "major_section": chunk.get("major_section") or "",
            "category": chunk.get("category") or "",
            "printed_page": chunk.get("printed_page"),
            "section_printed_page": chunk.get(
                "section_printed_page",
                chunk.get("printed_page"),
            ),
            "estimated_printed_page": chunk.get("estimated_printed_page"),
            "printed_page_offset": chunk.get("printed_page_offset"),
            "running_header": chunk.get("running_header") or "",
            "char_count": chunk.get("char_count", len(text)),
            "char_start": chunk.get("char_start"),
            "char_end": chunk.get("char_end"),
            "source_char_start": chunk.get("source_char_start"),
            "source_char_end": chunk.get("source_char_end"),
            "preview": preview,
        })

    return index_entries


def save_structural_index(output_path: str | Path, index_entries: list[dict[str, Any]]) -> None:
    """
    Save the structural index to disk as JSON.
    """
    output_path = Path(output_path)
    output_path.write_text(
        json.dumps(index_entries, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
