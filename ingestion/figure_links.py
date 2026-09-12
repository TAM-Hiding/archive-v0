from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ingestion.figure_layout import normalize_figure_caption


def load_figure_records(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    manifest_path = Path(metadata.get("figure_layout_file", ""))
    if not manifest_path.is_file():
        return []
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return list(payload.get("figures", []))


def _entry_body(entry: dict[str, Any], cleaned_text: str) -> str:
    start = entry.get("source_char_start")
    end = entry.get("source_char_end")
    if start is None or end is None:
        return entry.get("preview", "")
    try:
        return cleaned_text[int(start):int(end)]
    except (TypeError, ValueError):
        return entry.get("preview", "")


def link_figure_layouts_to_entries(
    entries: list[dict[str, Any]],
    layouts: list[dict[str, Any]],
    cleaned_text: str,
) -> int:
    """Link each figure to its caption-bearing or nearest same-page entry."""
    for entry in entries:
        entry.pop("figure_layout_ids", None)
        entry.pop("figure_search_text", None)

    linked_count = 0
    for layout in layouts:
        page_number = layout.get("page_number")
        candidates = [
            entry for entry in entries
            if entry.get("page_start") == page_number
        ]
        if not candidates:
            continue

        caption_key = layout.get("caption_key") or normalize_figure_caption(
            layout.get("caption", "")
        )
        target = next(
            (
                entry for entry in candidates
                if caption_key
                and caption_key in normalize_figure_caption(
                    _entry_body(entry, cleaned_text)
                )
            ),
            candidates[0],
        )
        target.setdefault("figure_layout_ids", []).append(layout["layout_id"])
        search_text = layout.get("label_text", "").strip()
        existing_search_text = target.get("figure_search_text", "").strip()
        if search_text and search_text not in existing_search_text:
            target["figure_search_text"] = "\n\n".join(
                value for value in (existing_search_text, search_text) if value
            )
        linked_count += 1

    return linked_count


def restore_figure_layout_links(
    entries: list[dict[str, Any]],
    metadata: dict[str, Any],
    cleaned_text: str,
) -> int:
    return link_figure_layouts_to_entries(
        entries,
        load_figure_records(metadata),
        cleaned_text,
    )
