from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ingestion.table_layout import (
    match_layout_to_caption,
    normalize_table_caption,
)


def load_table_layout_records(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    """Load compact table records suitable for linking structural entries."""
    layout_file = Path(metadata.get("table_layout_file", ""))
    if not layout_file.is_file():
        return []

    try:
        payload = json.loads(layout_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    records: list[dict[str, Any]] = []
    for layout in payload.get("layouts", []):
        record = dict(layout)
        record["caption_key"] = record.get("caption_key") or (
            normalize_table_caption(record.get("caption", ""))
        )
        records.append(record)
    return records


def link_table_layouts_to_entries(
    entries: list[dict[str, Any]],
    layouts: list[dict[str, Any]],
) -> int:
    """Restore layout IDs after rebuilding a document's structural index."""
    linked_entry_count = 0
    for entry in entries:
        if entry.get("content_type") != "table":
            continue
        page_number = entry.get("page_start")
        if page_number is None:
            continue
        layout = match_layout_to_caption(
            layouts,
            int(page_number),
            entry.get("table_caption", ""),
        )
        if layout is None:
            continue
        entry["table_layout_id"] = layout["layout_id"]
        linked_entry_count += 1
    return linked_entry_count


def restore_table_layout_links(
    entries: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> int:
    """Link rebuilt entries using an existing table-layout manifest."""
    return link_table_layouts_to_entries(
        entries,
        load_table_layout_records(metadata),
    )
