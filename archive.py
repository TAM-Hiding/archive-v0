import os
import json
import shutil
import string
import re
import difflib
import hashlib
from ingestion.indexer import (
    index_chunks_to_generated_notes,
    index_structural_doc_to_generated_note,
)
RESET = "\033[0m"
BOLD = "\033[1m"

YELLOW = "\033[93m"
CYAN = "\033[96m"
GREEN = "\033[92m"
RED = "\033[91m"
MAGENTA = "\033[95m"

PAGE_QUERY_PATTERN = re.compile(
    r"\b(?:pages?|p)\.?\s*#?\s*(\d+)\b",
    re.IGNORECASE,
)

def color_text(text, color, bold=False):
    if bold:
        return f"{BOLD}{color}{text}{RESET}"
    return f"{color}{text}{RESET}"

def build_vocabulary(notes):
    vocabulary = set()

    for note in notes:
        vocabulary.update(note["title_search"].split())
        vocabulary.update(note["tags"])
        vocabulary.update(note["aliases"])
        vocabulary.update(note["body_search"].split())
        vocabulary.update(note["path_search"].split())

    return vocabulary
    
def load_notes():
    notes = []

    for root, dirs, files in os.walk(notes_path):
        for file in files:
            if file.endswith(".md"):
                full_path = os.path.join(root, file)

                with open(full_path, "r") as f:
                    lines = f.readlines()

                    title = ""
                    tags = []
                    aliases = []
                    extra_meta = {}
                    body_lines = []

                    in_metadata = True

                    for line in lines:
                        stripped = line.strip()

                        if in_metadata:
                            if not stripped:
                                in_metadata = False
                                continue

                            if ":" in stripped:
                                key, value = stripped.split(":", 1)
                                key = key.strip().lower()
                                value = value.strip()

                                if key == "title":
                                    title = value

                                elif key in ("tags", "tag"):
                                    tags = [tag.strip().lower() for tag in value.split(",") if tag.strip()]

                                elif key in ("aliases", "alias"):
                                    aliases = [alias.strip().lower() for alias in value.split(",") if alias.strip()]

                                else:
                                    extra_meta[key] = value

                                continue

                            # if a non-empty line appears before a blank line and
                            # does not look like metadata, treat that as body start
                            in_metadata = False

                        body_lines.append(stripped)

                    body = "\n".join(body_lines).strip()
                    path_search = full_path.lower().replace("_", " ")

                    relative_path = os.path.relpath(full_path, notes_path)
                    relative_dir = os.path.dirname(relative_path)

                    if relative_dir in ("", "."):
                        category = ""
                        category_parts = []
                    else:
                        category_parts = relative_dir.split(os.sep)
                        category = " > ".join(category_parts)

                    is_generated = category_parts[:1] == ["_generated"]
                    if is_generated:
                        note_origin = "generated"
                    elif category_parts[:1] == ["_system"]:
                        note_origin = "system"
                    else:
                        note_origin = "manual"

                    note = {
                        "id": len(notes),
                        "title": title,
                        "title_search": title.lower(),
                        "tags": tags,
                        "aliases": aliases,
                        "meta": extra_meta,
                        "body": body,
                        "body_search": body.lower(),
                        "path": full_path,
                        "relative_path": relative_path,
                        "path_search": path_search,
                        "category": category,
                        "category_parts": category_parts,
                        "is_generated": is_generated,
                        "note_origin": note_origin,
                    }

                    notes.append(note)

    return notes

def get_note_by_id(note_id, notes):
    """
    Find a note by stable note_id.
    """
    for note in notes:
        meta = note.get("meta", {})

        if meta.get("note_id") == note_id:
            return note

    return None

def highlight_text(text, terms):
    for term in terms:
        if term in text:
            text = text.replace(
                term,
                f"\033[93m{term}\033[0m"
            )
    return text


def parse_page_query(query):
    """Return an explicit page locator and the remaining text query."""
    match = PAGE_QUERY_PATTERN.search(query)
    if match is None:
        return None, query

    page_number = int(match.group(1))
    remaining_query = (
        query[:match.start()] + " " + query[match.end():]
    ).strip()
    return page_number, remaining_query


def value_as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def page_range_contains(meta, page_number):
    page_start = value_as_int(meta.get("page_start"))
    page_end = value_as_int(meta.get("page_end"))
    if page_start is None:
        return False
    if page_end is None:
        page_end = page_start
    return page_start <= page_number <= page_end


def structural_heading_is_debris(heading):
    """Identify formula fragments and generic running headers used as titles."""
    normalized = " ".join(re.findall(r"[a-z0-9]+", heading.casefold()))
    if not normalized or normalized in {"table", "tables"}:
        return True

    words = re.findall(r"[a-z]+", heading.casefold())
    return not any(len(word) >= 4 for word in words)


def structural_result_title(entry, document):
    """Choose a useful search label without promoting equation debris."""
    table_caption = entry.get("table_caption", "").strip()
    if table_caption:
        return table_caption

    for candidate in (
        entry.get("subheading", ""),
        entry.get("section_heading", ""),
        entry.get("category", ""),
        entry.get("major_section", ""),
    ):
        candidate = candidate.strip()
        if candidate and not structural_heading_is_debris(candidate):
            return candidate

    page_start = entry.get("page_start")
    if page_start is not None:
        return f"Page {page_start} · Extracted segment"
    return document.get("title", "")


def get_note_origin(note):
    """Classify a note without requiring a storage migration."""
    if note.get("is_generated"):
        return "generated"
    if note.get("category_parts", [])[:1] == ["_system"]:
        return "system"
    return "manual"


def search_notes(query, notes, vocabulary, scope="all"):
    page_number, text_query = parse_page_query(query)
    translator = str.maketrans("", "", string.punctuation)
    clean_query = text_query.translate(translator)

    query_terms = clean_query.split()
    query_terms = [term for term in query_terms if len(term) > 1]

    expanded_terms = []
    for term in query_terms:
        if term not in expanded_terms:
            expanded_terms.append(term)

        # Only allow fuzzy expansion for terms long enough to be trustworthy.
        if len(term) < 5:
            continue

        if len(term) <= 7:
            close_matches = difflib.get_close_matches(term, vocabulary, n=1, cutoff=0.9)
        else:
            close_matches = difflib.get_close_matches(term, vocabulary, n=2, cutoff=0.9)

        for match in close_matches:
            if match != term and match not in expanded_terms:
                expanded_terms.append(match)

    results = []

    for note in notes:
        note_origin = note.get("note_origin") or get_note_origin(note)
        if scope == "notes" and note_origin != "manual":
            continue
        if scope == "reference" and note_origin != "generated":
            continue

        score = 0

        if page_number is not None:
            if note_origin == "generated":
                if not page_range_contains(note.get("meta", {}), page_number):
                    continue
                score += 50
            else:
                page_phrase = re.compile(
                    rf"\b(?:pages?|p)\.?\s*#?\s*{page_number}\b",
                    re.IGNORECASE,
                )
                if not page_phrase.search(
                    f"{note.get('title', '')}\n{note.get('body', '')}"
                ):
                    continue
                score += 20
        
        for term in expanded_terms:
            if term in note["title_search"]:
                score += 5
            if term in note["tags"]:
                score += 3
            if term in note["aliases"]:
                score += 4
            if term in note["body_search"]:
                score += 1
            if term in note["path_search"]:
                score += 2

        if score > 0:
            if note.get("is_generated"):
                score -= 1

            results.append((score, note))

    results.sort(reverse=True, key=lambda x: x[0])

    source_hit_counts = {}
    adjusted_results = []

    for score, note in results:
        adjusted_score = score

        if note.get("is_generated"):
            source_doc_id = note.get("meta", {}).get("source_doc_id", "")

            if source_doc_id:
                seen_count = source_hit_counts.get(source_doc_id, 0)
                adjusted_score -= seen_count
                source_hit_counts[source_doc_id] = seen_count + 1

        adjusted_results.append((adjusted_score, note))

    adjusted_results.sort(reverse=True, key=lambda x: x[0])

    top_results = adjusted_results[:5]

    return top_results, expanded_terms

def search_structural_entries(query):
    page_number, text_query = parse_page_query(query)
    translator = str.maketrans("", "", string.punctuation)
    clean_query = text_query.translate(translator).lower()

    query_terms = [term for term in clean_query.split() if len(term) > 1]
    results = []

    for document in list_ingested_documents():
        if document.get("chunk_storage_mode") != "structural_only":
            continue

        structural_index_file = document.get("structural_index_file", "")
        if not structural_index_file or not os.path.isfile(structural_index_file):
            continue

        try:
            with open(structural_index_file, "r", encoding="utf-8") as f:
                entries = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue

        for entry in entries:
            heading = entry.get("section_heading", "")
            table_caption = entry.get("table_caption", "")
            display_title = structural_result_title(entry, document)
            preview = entry.get("preview", "")
            searchable_parts = []
            for value in (
                preview,
                entry.get("search_text", ""),
                entry.get("figure_search_text", ""),
            ):
                value = value.strip()
                if value and value not in searchable_parts:
                    searchable_parts.append(value)
            searchable_text = "\n\n".join(searchable_parts)

            heading_search = heading.lower()
            table_caption_search = table_caption.lower()
            content_search = searchable_text.lower()
            retrieval_chunk_index = entry.get("retrieval_chunk_index")
            is_first_retrieval_chunk = retrieval_chunk_index in (None, 1)

            score = 0

            if page_number is not None:
                if not page_range_contains(entry, page_number):
                    continue
                score += 50
                if entry.get("content_type") == "table":
                    score += 20
                elif entry.get("figure_layout_ids"):
                    score += 10

            for term in query_terms:
                if term in heading_search:
                    score += 5
                if is_first_retrieval_chunk and term in table_caption_search:
                    score += 5
                if term in content_search:
                    score += 1

            if score <= 0:
                continue

            result = {
                "id": f"structural:{document['doc_id']}:{entry['entry_index']}",
                "title": display_title,
                "title_search": display_title.casefold(),
                "tags": [],
                "aliases": [],
                "meta": {
                    "source_doc_id": document.get("doc_id", ""),
                    "source_filename": document.get("source_filename", ""),
                    "entry_index": entry.get("entry_index"),
                    "chunk_index": entry.get("chunk_index"),
                    "semantic_unit_id": entry.get("semantic_unit_id"),
                    "semantic_unit_index": entry.get("semantic_unit_index"),
                    "semantic_unit_page_start": entry.get(
                        "semantic_unit_page_start"
                    ),
                    "semantic_unit_page_end": entry.get(
                        "semantic_unit_page_end"
                    ),
                    "semantic_unit_char_count": entry.get(
                        "semantic_unit_char_count"
                    ),
                    "semantic_unit_block_count": entry.get(
                        "semantic_unit_block_count"
                    ),
                    "retrieval_chunk_index": entry.get("retrieval_chunk_index"),
                    "retrieval_chunk_count": entry.get("retrieval_chunk_count"),
                    "content_type": entry.get("content_type", "prose"),
                    "table_caption": table_caption,
                    "table_layout_id": entry.get("table_layout_id"),
                    "figure_layout_ids": entry.get("figure_layout_ids", []),
                    "page_start": entry.get("page_start"),
                    "page_end": entry.get("page_end"),
                    "structural_hit": True,
                },
                "body": searchable_text,
                "body_search": content_search,
                "path": structural_index_file,
                "relative_path": structural_index_file,
                "path_search": structural_index_file.lower().replace("_", " "),
                "category": document.get("category_path", "").replace("/", " > "),
                "category_parts": [
                    part
                    for part in document.get("category_path", "").split("/")
                    if part
                ],
                "is_generated": True,
            }

            results.append((score, result))

    results.sort(reverse=True, key=lambda x: x[0])

    # A recovered table or figure can span several retrieval chunks. Search
    # each chunk for recall, but show the best-matching child only once.
    deduplicated_results = []
    seen_artifacts = set()
    for score, result in results:
        artifact_key = structural_artifact_key(result.get("meta", {}))
        if artifact_key:
            document_key = result.get("meta", {}).get("source_doc_id", "")
            qualified_key = (document_key, artifact_key)
            if qualified_key in seen_artifacts:
                continue
            seen_artifacts.add(qualified_key)
        deduplicated_results.append((score, result))

    return deduplicated_results[:5]


FRONT_MATTER_HEADINGS = {
    "acknowledgments",
    "acknowledgements",
    "about this edition",
    "contributors",
    "copyright",
    "foreword",
    "front matter",
    "preface",
    "title page",
}


def structural_front_matter_label(entry):
    """Return a collapsible navigation label for known front-matter entries."""
    if entry.get("content_type") == "contents":
        return "Table of Contents"

    heading = " ".join(
        re.findall(r"[a-z0-9]+", entry.get("section_heading", "").casefold())
    )
    if heading not in FRONT_MATTER_HEADINGS:
        return None

    if heading == "front matter":
        return "Front Matter"
    return entry.get("section_heading", "").strip() or heading.title()


def structural_artifact_key(entry):
    """Return a stable key for retrieval chunks representing one artifact."""
    content_type = entry.get("content_type", "prose")
    figure_layout_ids = tuple(sorted(entry.get("figure_layout_ids") or []))
    semantic_unit_id = entry.get("semantic_unit_id")

    if content_type == "table":
        table_layout_id = entry.get("table_layout_id")
        if table_layout_id:
            return ("table-layout", table_layout_id)
        if semantic_unit_id:
            return ("table-unit", semantic_unit_id)

    if figure_layout_ids:
        return ("figures", figure_layout_ids)

    return None


def _merge_artifact_entry(existing, entry):
    """Fold another retrieval chunk into an artifact navigation card."""
    merged = dict(existing)
    merged["display_chunk_count"] = merged.get("display_chunk_count", 1) + 1

    page_starts = [
        page for page in (merged.get("page_start"), entry.get("page_start"))
        if isinstance(page, int)
    ]
    page_ends = [
        page for page in (merged.get("page_end"), entry.get("page_end"))
        if isinstance(page, int)
    ]
    if page_starts:
        merged["page_start"] = min(page_starts)
    if page_ends:
        merged["page_end"] = max(page_ends)

    merged["char_count"] = (
        (merged.get("char_count") or 0) + (entry.get("char_count") or 0)
    )
    merged["figure_layout_ids"] = list(dict.fromkeys(
        (merged.get("figure_layout_ids") or [])
        + (entry.get("figure_layout_ids") or [])
    ))
    return merged


def _append_display_entry(target, entry):
    """Append an entry, coalescing adjacent chunks of the same artifact."""
    artifact_key = structural_artifact_key(entry)
    if target and artifact_key:
        previous = target[-1]
        if structural_artifact_key(previous) == artifact_key:
            target[-1] = _merge_artifact_entry(previous, entry)
            return

    display_entry = dict(entry)
    if artifact_key:
        display_entry["display_chunk_count"] = 1
    target.append(display_entry)


def build_structural_display_items(entries):
    """Build compact navigation groups without changing stored chunks."""
    display_items = []

    # The opening contents run gives us a reliable body boundary even when
    # title-page fragments have misleading headings. Entries through that run
    # are front matter; explicit headings provide the nested group names and
    # unlabeled continuations inherit the prior name. Later section-level
    # contents remain independent body entries.
    first_contents_index = next(
        (
            index
            for index, entry in enumerate(entries)
            if entry.get("content_type") == "contents"
        ),
        None,
    )
    front_matter_end = -1
    if first_contents_index is not None:
        front_matter_end = first_contents_index
        for index in range(first_contents_index + 1, len(entries)):
            if entries[index].get("content_type") != "contents":
                break
            front_matter_end = index
    active_front_matter_label = None

    for index, entry in enumerate(entries):
        explicit_label = structural_front_matter_label(entry)
        if index <= front_matter_end:
            if explicit_label:
                active_front_matter_label = explicit_label
            elif active_front_matter_label is None:
                active_front_matter_label = "Publication Details"
            label = active_front_matter_label
        else:
            label = explicit_label
        previous = display_items[-1] if display_items else None

        if label and previous and previous.get("kind") == "group" and previous.get("label") == label:
            _append_display_entry(previous["entries"], entry)
            previous["entry_count"] += 1
            page_start = entry.get("page_start")
            page_end = entry.get("page_end")
            if isinstance(page_start, int):
                previous["page_start"] = min(previous["page_start"], page_start)
            if isinstance(page_end, int):
                previous["page_end"] = max(previous["page_end"], page_end)
            continue

        if label:
            page_start = entry.get("page_start")
            page_end = entry.get("page_end")
            display_items.append({
                "kind": "group",
                "label": label,
                "entries": [],
                "entry_count": 1,
                "page_start": page_start if isinstance(page_start, int) else 0,
                "page_end": page_end if isinstance(page_end, int) else 0,
            })
            _append_display_entry(display_items[-1]["entries"], entry)
        else:
            artifact_key = structural_artifact_key(entry)
            if (
                artifact_key
                and previous
                and previous.get("kind") == "entry"
                and structural_artifact_key(previous.get("entry", {})) == artifact_key
            ):
                previous["entry"] = _merge_artifact_entry(
                    previous["entry"], entry
                )
            else:
                display_entry = dict(entry)
                if artifact_key:
                    display_entry["display_chunk_count"] = 1
                display_items.append({"kind": "entry", "entry": display_entry})

    return display_items

def extract_chunk_index_from_filename(filename):
    parts = filename.rsplit("__chunk_", 1)
    if len(parts) != 2:
        return None

    chunk_part = parts[1]
    if chunk_part.endswith(".md"):
        chunk_part = chunk_part[:-3]

    if not chunk_part.isdigit():
        return None

    return int(chunk_part)

def get_source_context(note, notes):
    def build_context_entry(note_obj, chunk_index):
        if note_obj is None:
            return None

        return {
            "note": note_obj,
            "chunk_index": chunk_index
        }

    if not note.get("is_generated"):
        return {
            "previous": None,
            "current": build_context_entry(note, None),
            "next": None
        }

    source_doc_id = note.get("meta", {}).get("source_doc_id")
    if not source_doc_id:
        return {
            "previous": None,
            "current": build_context_entry(note, None),
            "next": None
        }

    sibling_chunks = []

    for candidate in notes:
        if not candidate.get("is_generated"):
            continue

        candidate_source_doc_id = candidate.get("meta", {}).get("source_doc_id")
        if candidate_source_doc_id != source_doc_id:
            continue

        chunk_index_raw = candidate.get("meta", {}).get("chunk_index")
        if chunk_index_raw is None:
            filename = os.path.basename(candidate.get("path", ""))
            chunk_index_raw = extract_chunk_index_from_filename(filename)

        if chunk_index_raw is None:
            continue

        try:
            chunk_index = int(chunk_index_raw)
        except ValueError:
            continue

        sibling_chunks.append((chunk_index, candidate))

    sibling_chunks.sort(key=lambda x: x[0])

    current_position = None
    current_path = note.get("path")

    for i, (chunk_index, candidate) in enumerate(sibling_chunks):
        if candidate.get("path") == current_path:
            current_position = i
            break

    if current_position is None:
        return {
            "previous": None,
            "current": build_context_entry(note, None),
            "next": None
        }

    previous_entry = None
    if current_position > 0:
        prev_chunk_index, prev_note = sibling_chunks[current_position - 1]
        previous_entry = build_context_entry(prev_note, prev_chunk_index)

    current_chunk_index, current_note = sibling_chunks[current_position]
    current_entry = build_context_entry(current_note, current_chunk_index)

    next_entry = None
    if current_position < len(sibling_chunks) - 1:
        next_chunk_index, next_note = sibling_chunks[current_position + 1]
        next_entry = build_context_entry(next_note, next_chunk_index)

    return {
        "previous": previous_entry,
        "current": current_entry,
        "next": next_entry
    }

def get_source_document(note, notes):
    if not note.get("is_generated"):
        return None

    source_doc_id = note.get("meta", {}).get("source_doc_id")
    if not source_doc_id:
        return None

    if note.get("meta", {}).get("chunk_storage_mode") == "structural_only":
        meta = note.get("meta", {})

        return {
            "mode": "structural_only",
            "source_doc_id": source_doc_id,
            "title": note.get("title"),
            "source_filename": meta.get("source_filename"),
            "page_count": meta.get("page_count"),
            "chunk_count_estimate": meta.get("chunk_count_estimate"),
            "structural_index_file": meta.get("structural_index_file"),
            "current_path": note.get("path"),
            "overview_note": note,
            "chunks": []
        }

    source_chunks = []

    for candidate in notes:
        if not candidate.get("is_generated"):
            continue

        candidate_source_doc_id = candidate.get("meta", {}).get("source_doc_id")
        if candidate_source_doc_id != source_doc_id:
            continue

        chunk_index_raw = candidate.get("meta", {}).get("chunk_index")
        if chunk_index_raw is None:
            filename = os.path.basename(candidate.get("path", ""))
            chunk_index_raw = extract_chunk_index_from_filename(filename)

        if chunk_index_raw is None:
            continue

        try:
            chunk_index = int(chunk_index_raw)
        except ValueError:
            continue

        source_chunks.append({
            "note": candidate,
            "chunk_index": chunk_index,
            "is_current": candidate.get("path") == note.get("path")
        })

    source_chunks.sort(key=lambda chunk: chunk["chunk_index"])

    return {
        "source_doc_id": source_doc_id,
        "title": note.get("meta", {}).get("source_filename") or note.get("title"),
        "current_path": note.get("path"),
        "chunks": source_chunks
    }
    
def list_ingested_documents():
    documents = []

    if not os.path.isdir(archive_documents_path):
        return documents

    for doc_id in os.listdir(archive_documents_path):
        doc_root = os.path.join(archive_documents_path, doc_id)

        if not os.path.isdir(doc_root):
            continue

        metadata_file = os.path.join(doc_root, "metadata.json")
        if not os.path.isfile(metadata_file):
            continue

        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue

        category_path = metadata.get("category_path", "").strip("/")
        generated_output_dir = os.path.join(generated_notes_path, *[part for part in category_path.split("/") if part], doc_id)

        documents.append({
            "doc_id": metadata.get("doc_id", doc_id),
            "title": metadata.get("title", ""),
            "source_filename": metadata.get("source_filename", ""),
            "stored_source_filename": metadata.get(
                "stored_source_filename",
                "",
            ),
            "category_path": category_path,
            "status": metadata.get("status", ""),
            "chunk_count": metadata.get("chunk_count", 0),
            "page_count": metadata.get("page_count", 0),

            "chunk_storage_mode": metadata.get("chunk_storage_mode", ""),
            "chunk_count_estimate": metadata.get("chunk_count_estimate", 0),
            "structural_index_file": metadata.get("structural_index_file", ""),
            "structural_index_entry_count": metadata.get("structural_index_entry_count", 0),
            "table_layout_file": metadata.get("table_layout_file", ""),
            "table_layout_storage_mode": metadata.get(
                "table_layout_storage_mode",
                "",
            ),
            "figure_layout_file": metadata.get("figure_layout_file", ""),
            "figure_layout_storage_mode": metadata.get(
                "figure_layout_storage_mode",
                "",
            ),
            "promoted_chunk_count": metadata.get("promoted_chunk_count", 0),

            "metadata_file": metadata_file,
            "doc_root": doc_root,
            "cleaned_text_file": metadata.get("cleaned_text_file", ""),
            "generated_output_dir": generated_output_dir,
            "has_generated_output": os.path.isdir(generated_output_dir),
            "updated_at": metadata.get("updated_at", ""),
            "created_at": metadata.get("created_at", "")
        })

    documents.sort(key=lambda doc: (doc["updated_at"], doc["doc_id"]), reverse=True)
    return documents

def get_ingested_document(doc_id):
    documents = list_ingested_documents()

    for document in documents:
        if document["doc_id"] == doc_id:
            return document

    return None

def get_source_note_for_document(doc_id, notes):
    document = get_ingested_document(doc_id)

    if document is None:
        return None

    matching_notes = []

    for note in notes:
        if not note.get("is_generated"):
            continue

        source_doc_id = note.get("meta", {}).get("source_doc_id")
        if source_doc_id == doc_id:
            matching_notes.append(note)

    if not matching_notes:
        return None

    # Prefer the structural-only document note if present.
    for note in matching_notes:
        if note.get("meta", {}).get("chunk_storage_mode") == "structural_only":
            return note

    # Otherwise prefer chunk 0 / first chunk if available.
    def sort_key(note):
        chunk_index = note.get("meta", {}).get("chunk_index")
        try:
            return (0, int(chunk_index))
        except (TypeError, ValueError):
            return (1, note.get("path", ""))

    matching_notes.sort(key=sort_key)
    return matching_notes[0]

def get_structural_index_for_document(doc_id):
    document = get_ingested_document(doc_id)

    if document is None:
        return None

    structural_index_file = document.get("structural_index_file", "")
    if not structural_index_file or not os.path.isfile(structural_index_file):
        return None

    try:
        with open(structural_index_file, "r", encoding="utf-8") as f:
            entries = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    return {
        "document": document,
        "entries": entries,
        "display_items": build_structural_display_items(entries),
    }


def normalize_table_series_caption(caption):
    """Normalize a caption while ignoring PDF continuation markers."""
    without_continued = re.sub(
        r"\(?\bcontinued\b\)?",
        " ",
        caption.casefold(),
    )
    return " ".join(re.findall(r"[a-z0-9]+", without_continued))


PDF_MATH_DELIMITER_RUNS = (
    (re.compile(r"(?:[\uf0e6-\uf0e8]\s*)+"), "("),
    (re.compile(r"(?:[\uf0f6-\uf0f8]\s*)+"), ")"),
    (re.compile(r"(?:[\uf0e9-\uf0eb]\s*)+"), "["),
    (re.compile(r"(?:[\uf0f9-\uf0fb]\s*)+"), "]"),
    (re.compile(r"(?:[\uf0ec-\uf0ef]\s*)+"), "{"),
    (re.compile(r"(?:[\uf0fc-\uf0fe]\s*)+"), "}"),
)


def normalize_pdf_math_glyphs(text):
    """Replace legacy Symbol-font delimiter pieces with readable Unicode."""
    if not isinstance(text, str) or not text:
        return text

    normalized = text
    for pattern, replacement in PDF_MATH_DELIMITER_RUNS:
        normalized = pattern.sub(replacement, normalized)
    return normalized


def table_layout_for_display(layout):
    """Copy a recovered layout and normalize only its displayed text."""
    display_layout = dict(layout)
    display_layout["caption"] = normalize_pdf_math_glyphs(
        layout.get("caption", "")
    )
    display_layout["reading_order_text"] = normalize_pdf_math_glyphs(
        layout.get("reading_order_text", "")
    )
    display_layout["grid"] = [
        [normalize_pdf_math_glyphs(cell) for cell in row]
        for row in layout.get("grid", [])
    ]
    return display_layout


def _load_table_layout_shard(layout_file, layout_record):
    manifest_root = os.path.realpath(os.path.dirname(layout_file))
    shard_path = os.path.realpath(
        os.path.join(manifest_root, layout_record.get("file", ""))
    )
    try:
        if os.path.commonpath([manifest_root, shard_path]) != manifest_root:
            return None
    except ValueError:
        return None

    try:
        with open(shard_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def get_table_layouts_for_entry(document, entry):
    """Load the contiguous logical table series linked to one entry."""
    layout_id = entry.get("table_layout_id")
    layout_file = document.get("table_layout_file", "")
    if not layout_id or not layout_file or not os.path.isfile(layout_file):
        return []

    try:
        with open(layout_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []

    if manifest.get("storage_mode") != "sharded":
        layouts = manifest.get("layouts", [])
        target = next(
            (layout for layout in layouts if layout.get("layout_id") == layout_id),
            None,
        )
        if target is None:
            return []
        target_identity = normalize_table_series_caption(
            target.get("caption", "")
        )
        if not target_identity:
            return [target]
        matching = sorted(
            (
                layout
                for layout in layouts
                if normalize_table_series_caption(layout.get("caption", ""))
                == target_identity
            ),
            key=lambda layout: (
                layout.get("page_number", 0),
                layout.get("table_index", 0),
            ),
        )
        return _contiguous_table_series(matching, layout_id)

    layout_records = manifest.get("layouts", [])
    target_record = next(
        (
            layout
            for layout in layout_records
            if layout.get("layout_id") == layout_id
        ),
        None,
    )
    if target_record is None:
        return []

    target_identity = normalize_table_series_caption(
        target_record.get("caption", "")
    )
    if not target_identity:
        layout = _load_table_layout_shard(layout_file, target_record)
        return [layout] if layout is not None else []
    matching_records = sorted(
        (
            record
            for record in layout_records
            if normalize_table_series_caption(record.get("caption", ""))
            == target_identity
        ),
        key=lambda record: (
            record.get("page_number", 0),
            record.get("table_index", 0),
        ),
    )
    series_records = _contiguous_table_series(matching_records, layout_id)
    return [
        layout
        for layout in (
            _load_table_layout_shard(layout_file, record)
            for record in series_records
        )
        if layout is not None
    ]


def _contiguous_table_series(layouts, target_layout_id):
    """Return the same-caption component connected by adjacent PDF pages."""
    target_index = next(
        (
            index
            for index, layout in enumerate(layouts)
            if layout.get("layout_id") == target_layout_id
        ),
        None,
    )
    if target_index is None:
        return []

    start = target_index
    end = target_index
    while start > 0:
        current_page = layouts[start].get("page_number", 0)
        previous_page = layouts[start - 1].get("page_number", 0)
        if current_page - previous_page > 1:
            break
        start -= 1

    while end + 1 < len(layouts):
        current_page = layouts[end].get("page_number", 0)
        next_page = layouts[end + 1].get("page_number", 0)
        if next_page - current_page > 1:
            break
        end += 1

    return layouts[start:end + 1]


def get_table_layout_for_entry(document, entry):
    """Compatibility helper returning the exact linked table layout."""
    layout_id = entry.get("table_layout_id")
    layouts = get_table_layouts_for_entry(document, entry)
    return next(
        (layout for layout in layouts if layout.get("layout_id") == layout_id),
        None,
    )


def _load_figure_manifest(document):
    manifest_path = document.get("figure_layout_file", "")
    if not manifest_path or not os.path.isfile(manifest_path):
        return None
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def get_figure_layouts_for_entries(document, entries):
    manifest = _load_figure_manifest(document)
    if manifest is None:
        return []
    requested_ids = []
    for entry in entries:
        for layout_id in entry.get("figure_layout_ids", []):
            if layout_id not in requested_ids:
                requested_ids.append(layout_id)
    records_by_id = {
        record.get("layout_id"): record
        for record in manifest.get("figures", [])
    }
    return [
        records_by_id[layout_id]
        for layout_id in requested_ids
        if layout_id in records_by_id
    ]


def figure_label_text(layout):
    """Return only figure labels through the caption, excluding later prose."""
    label_text = layout.get("label_text", "").strip()
    caption = layout.get("caption", "").strip()
    if not label_text or not caption:
        return label_text
    caption_start = label_text.find(caption)
    if caption_start < 0:
        return label_text
    return label_text[:caption_start + len(caption)].strip()


def remove_figure_labels_from_body(body, layouts):
    """Hide duplicated diagram labels while preserving the untouched source."""
    display_body = body
    removed_labels = []
    for layout in layouts:
        label_text = figure_label_text(layout)
        tokens = re.findall(r"\S+", label_text)
        if not tokens:
            continue
        pattern = r"\s+".join(re.escape(token) for token in tokens)
        display_body, replacements = re.subn(
            pattern,
            "",
            display_body,
            count=1,
            flags=re.DOTALL,
        )
        if replacements:
            removed_labels.append(label_text)
    display_body = re.sub(r"\n(?:[ \t]*\n){2,}", "\n\n", display_body)
    return display_body.strip(), removed_labels


def get_figure_image_path(doc_id, layout_id):
    """Resolve a manifest-listed figure image without accepting raw paths."""
    if not doc_id or os.path.basename(doc_id) != doc_id:
        return None
    if not layout_id or os.path.basename(layout_id) != layout_id:
        return None
    document = get_ingested_document(doc_id)
    if document is None:
        return None
    manifest = _load_figure_manifest(document)
    if manifest is None:
        return None
    record = next(
        (
            item for item in manifest.get("figures", [])
            if item.get("layout_id") == layout_id
        ),
        None,
    )
    if record is None:
        return None
    manifest_root = os.path.realpath(
        os.path.dirname(document.get("figure_layout_file", ""))
    )
    image_path = os.path.realpath(
        os.path.join(manifest_root, record.get("file", ""))
    )
    try:
        if os.path.commonpath([manifest_root, image_path]) != manifest_root:
            return None
    except ValueError:
        return None
    return image_path if os.path.isfile(image_path) else None


def get_source_page_preview_path(doc_id, page_number):
    """Return a cached PNG rendered from an ingested document's source PDF."""
    if not doc_id or os.path.basename(doc_id) != doc_id:
        return None
    try:
        page_number = int(page_number)
    except (TypeError, ValueError):
        return None
    if page_number < 1:
        return None

    document = get_ingested_document(doc_id)
    if document is None:
        return None

    stored_filename = document.get("stored_source_filename", "")
    if (
        not stored_filename
        or os.path.basename(stored_filename) != stored_filename
        or not stored_filename.lower().endswith(".pdf")
    ):
        return None

    if not document.get("doc_root"):
        return None
    doc_root = os.path.realpath(document["doc_root"])
    source_path = os.path.realpath(os.path.join(doc_root, stored_filename))
    try:
        if os.path.commonpath([doc_root, source_path]) != doc_root:
            return None
    except ValueError:
        return None
    if not os.path.isfile(source_path):
        return None

    preview_directory = os.path.join(doc_root, "source_previews")
    preview_path = os.path.join(
        preview_directory,
        f"page_{page_number:04d}.png",
    )
    if (
        os.path.isfile(preview_path)
        and os.path.getmtime(preview_path) >= os.path.getmtime(source_path)
    ):
        return preview_path

    from ingestion.source_preview import render_pdf_page_preview

    try:
        return str(render_pdf_page_preview(
            source_path,
            page_number,
            preview_path,
        ))
    except (OSError, ValueError, RuntimeError):
        return None


def source_verification_pages(table_layouts, context_entries, warning=False):
    """Choose the smallest useful set of original PDF pages for verification."""
    table_pages = sorted({
        page_number
        for page_number in (
            value_as_int(layout.get("page_number"))
            for layout in table_layouts
        )
        if page_number is not None and page_number > 0
    })
    if table_pages:
        return table_pages[:8]
    if not warning:
        return []

    equation_pages = set()
    for item in context_entries:
        entry = item.get("entry", item)
        if entry.get("layout_hint") != "equation":
            continue
        start = value_as_int(entry.get("page_start"))
        end = value_as_int(entry.get("page_end"))
        if start is None:
            continue
        end = end if end is not None and end >= start else start
        equation_pages.update(range(start, end + 1))

    return sorted(equation_pages)[:8]


def get_structural_segment(doc_id, entry_index):
    structural_document = get_structural_index_for_document(doc_id)

    if structural_document is None:
        return None

    entries = structural_document["entries"]
    document = structural_document["document"]

    if entry_index < 0 or entry_index >= len(entries):
        return None

    cleaned_text = ""
    cleaned_text_file = document.get("cleaned_text_file", "")

    if cleaned_text_file and os.path.isfile(cleaned_text_file):
        with open(cleaned_text_file, "r", encoding="utf-8") as f:
            cleaned_text = f.read()

    def build_entry(index):
        if index < 0 or index >= len(entries):
            return None

        entry = entries[index]
        body = entry.get("preview", "")

        source_char_start = entry.get("source_char_start")
        source_char_end = entry.get("source_char_end")

        if (
            cleaned_text
            and source_char_start is not None
            and source_char_end is not None
        ):
            try:
                body = cleaned_text[
                    int(source_char_start):int(source_char_end)
                ].strip()
            except (TypeError, ValueError):
                body = entry.get("preview", "")

        return {
            "entry": entry,
            "entry_index": index,
            "body": body,
            "display_heading": structural_result_title(entry, document),
            "heading_is_suspect": bool(
                entry.get("section_heading")
                and structural_heading_is_debris(
                    entry.get("section_heading", "")
                )
            ),
        }

    current = build_entry(entry_index)
    current_entry = entries[entry_index]
    table_layouts = [
        table_layout_for_display(layout)
        for layout in get_table_layouts_for_entry(document, current_entry)
    ]
    table_layout = next(
        (
            layout
            for layout in table_layouts
            if layout.get("layout_id") == current_entry.get("table_layout_id")
        ),
        None,
    )
    semantic_unit_id = current_entry.get("semantic_unit_id")
    context_entries = []
    context_mode = "legacy_neighbors"
    semantic_unit = None
    context_start = entry_index
    context_end = entry_index

    if semantic_unit_id:
        unit_start = entry_index
        unit_end = entry_index

        while (
            unit_start > 0
            and entries[unit_start - 1].get("semantic_unit_id")
            == semantic_unit_id
        ):
            unit_start -= 1

        while (
            unit_end + 1 < len(entries)
            and entries[unit_end + 1].get("semantic_unit_id")
            == semantic_unit_id
        ):
            unit_end += 1

        context_entries = [
            build_entry(index)
            for index in range(unit_start, unit_end + 1)
        ]
        context_start = unit_start
        context_end = unit_end
        context_mode = "semantic_unit"
        first_unit_entry = entries[unit_start]
        last_unit_entry = entries[unit_end]
        semantic_unit_char_count = current_entry.get(
            "semantic_unit_char_count"
        )

        if semantic_unit_char_count is None:
            semantic_unit_char_count = sum(
                entry.get("char_count", 0) or 0
                for entry in entries[unit_start:unit_end + 1]
            )

        semantic_unit = {
            "id": semantic_unit_id,
            "index": current_entry.get("semantic_unit_index"),
            "page_start": current_entry.get("semantic_unit_page_start")
            or first_unit_entry.get("page_start"),
            "page_end": current_entry.get("semantic_unit_page_end")
            or last_unit_entry.get("page_end"),
            "char_count": semantic_unit_char_count,
            "block_count": current_entry.get("semantic_unit_block_count"),
            "retrieval_chunk_count": current_entry.get(
                "retrieval_chunk_count"
            ) or len(context_entries),
            "section_heading": current_entry.get("section_heading"),
            "subheading": current_entry.get("subheading"),
            "content_type": current_entry.get("content_type", "prose"),
            "table_caption": current_entry.get("table_caption"),
            "display_heading": structural_result_title(
                current_entry,
                document,
            ),
            "heading_is_suspect": bool(
                current_entry.get("section_heading")
                and structural_heading_is_debris(
                    current_entry.get("section_heading", "")
                )
            ),
            "extraction_warning": any(
                entry.get("layout_hint") == "equation"
                and entry.get("section_heading")
                and structural_heading_is_debris(
                    entry.get("section_heading", "")
                )
                for entry in entries[unit_start:unit_end + 1]
            ),
        }

    figure_layouts = get_figure_layouts_for_entries(
        document,
        entries[context_start:context_end + 1],
    )
    figure_layouts_by_id = {
        layout.get("layout_id"): layout for layout in figure_layouts
    }
    displayed_items = (
        context_entries
        if context_mode == "semantic_unit"
        else [build_entry(entry_index - 1), current, build_entry(entry_index + 1)]
    )
    for item in displayed_items:
        if item is None:
            continue
        linked_layouts = [
            figure_layouts_by_id[layout_id]
            for layout_id in item["entry"].get("figure_layout_ids", [])
            if layout_id in figure_layouts_by_id
        ]
        display_body, removed_labels = remove_figure_labels_from_body(
            item["body"],
            linked_layouts,
        )
        item["display_body"] = normalize_pdf_math_glyphs(display_body)
        item["figure_labels"] = removed_labels

    extraction_warning = bool(
        semantic_unit and semantic_unit.get("extraction_warning")
    )
    verification_pages = source_verification_pages(
        table_layouts,
        context_entries if context_mode == "semantic_unit" else [current],
        warning=extraction_warning,
    )

    return {
        "document": document,
        "context_mode": context_mode,
        "context_entries": context_entries,
        "matched_entry_index": entry_index,
        "semantic_unit": semantic_unit,
        "table_layout": table_layout,
        "table_layouts": table_layouts,
        "figure_layouts": figure_layouts,
        "source_verification_pages": verification_pages,
        "source_verification_open": extraction_warning,
        "previous": (
            displayed_items[0]
            if context_mode != "semantic_unit"
            else build_entry(entry_index - 1)
        ),
        "current": current,
        "next": (
            displayed_items[2]
            if context_mode != "semantic_unit"
            else build_entry(entry_index + 1)
        ),
    }

def reindex_ingested_document(doc_id):
    document = get_ingested_document(doc_id)

    if document is None:
        return {
            "ok": False,
            "message": "Document not found."
        }

    try:
        if document.get("chunk_storage_mode") == "structural_only":
            index_result = index_structural_doc_to_generated_note(document["metadata_file"])
        else:
            index_result = index_chunks_to_generated_notes(document["metadata_file"])
    except Exception as e:
        return {
            "ok": False,
            "message": f"Re-index failed: {e}"
        }

    return {
        "ok": True,
        "message": "Generated output re-indexed successfully.",
        "document": get_ingested_document(doc_id),
        "index_result": index_result
    }

def delete_generated_output(doc_id):
    document = get_ingested_document(doc_id)

    if document is None:
        return {
            "ok": False,
            "message": "Document not found."
        }

    generated_output_dir = document.get("generated_output_dir", "")

    if not generated_output_dir or not os.path.isdir(generated_output_dir):
        return {
            "ok": False,
            "message": "No generated output directory found for this document."
        }

    try:
        shutil.rmtree(generated_output_dir)
    except Exception as e:
        return {
            "ok": False,
            "message": f"Delete failed: {e}"
        }

    return {
        "ok": True,
        "message": "Generated output deleted successfully.",
        "document": get_ingested_document(doc_id)
    }

def delete_note(path):
    if not path:
        return {
            "ok": False,
            "message": "No note path provided."
        }

    if not os.path.isfile(path):
        return {
            "ok": False,
            "message": "Note file not found."
        }

    # Safety: only delete files inside notes_path
    notes_root_abs = os.path.abspath(notes_path)
    note_path_abs = os.path.abspath(path)

    if not note_path_abs.startswith(notes_root_abs + os.sep):
        return {
            "ok": False,
            "message": "Refusing to delete file outside notes directory."
        }

    # Safety: do not delete generated notes here
    relative_path = os.path.relpath(note_path_abs, notes_root_abs)
    relative_parts = relative_path.split(os.sep)

    if relative_parts[:1] == ["_generated"]:
        return {
            "ok": False,
            "message": "Generated notes should be deleted through document curator generated-output controls."
        }

    try:
        os.remove(note_path_abs)
    except Exception as e:
        return {
            "ok": False,
            "message": f"Delete failed: {e}"
        }

    return {
        "ok": True,
        "message": "Note deleted successfully."
    }

notes_path = "notes"
archive_documents_path = os.path.join(notes_path, "_archive_data", "documents")
generated_notes_path = os.path.join(notes_path, "_generated")

def slugify_filename(title):
    safe = title.lower()
    safe = safe.replace(" ", "_")

    allowed = "abcdefghijklmnopqrstuvwxyz0123456789_-"
    safe = "".join(char for char in safe if char in allowed)

    while "__" in safe:
        safe = safe.replace("__", "_")

    safe = safe.strip("_")

    if not safe:
        safe = "untitled_note"

    return safe + ".md"

def generate_note_id(category, title):
    raw = f"{category}/{title}".strip().lower()
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"note_{digest}"

def save_note(title, tags, body, category, aliases=""):
    category = category.strip().strip("/")
    filename = slugify_filename(title)

    folder_path = os.path.join(notes_path, category) if category else notes_path
    os.makedirs(folder_path, exist_ok=True)

    full_path = os.path.join(folder_path, filename)

    # normalize aliases
    alias_list = [a.strip().lower() for a in aliases.split(",") if a.strip()]
    seen = set()
    cleaned_aliases = []

    for alias in alias_list:
        if alias not in seen:
            seen.add(alias)
            cleaned_aliases.append(alias)

    aliases_text = ", ".join(cleaned_aliases)
    
    note_id = generate_note_id(category, title)

    with open(full_path, "w") as f:
        f.write(f"title: {title}\n")
        f.write(f"note_id: {note_id}\n")
        f.write(f"tags: {tags}\n")
        f.write(f"aliases: {aliases_text}\n")
        f.write("\n")
        f.write(body.strip() + "\n")

    return full_path

def update_note(path, title, tags, body, aliases=""):
    # normalize aliases
    alias_list = [a.strip().lower() for a in aliases.split(",") if a.strip()]
    seen = set()
    cleaned_aliases = []

    for alias in alias_list:
        if alias not in seen:
            seen.add(alias)
            cleaned_aliases.append(alias)

    aliases_text = ", ".join(cleaned_aliases)
    
    with open(path, "w") as f:
        f.write(f"title: {title}\n")
        f.write(f"tags: {tags}\n")
        f.write(f"aliases: {aliases_text}\n")
        f.write("\n")
        f.write(body.strip() + "\n")

    return path

def build_folder_tree():
    tree = {}

    for root, dirs, files in os.walk(notes_path):
        rel_path = os.path.relpath(root, notes_path)

        if rel_path == ".":
            parts = []
        else:
            parts = rel_path.split(os.sep)

        current = tree
        for part in parts:
            current = current.setdefault(part, {})

        for d in dirs:
            current.setdefault(d, {})

    return tree

if __name__ == "__main__":
    notes = load_notes()
    vocabulary = build_vocabulary(notes)

# SEARCH LOOP
    while True:
        query = input(color_text("\nSearch (or type 'quit' / 'reload'): ", CYAN, bold=True)).lower().strip()
        if query == "reload":
             print(color_text("Reloading The Archive™...", GREEN, bold=True))
             notes = load_notes()
             vocabulary = build_vocabulary(notes)
             print(color_text("Reload complete.", GREEN, bold=True))
             continue

        if query == "quit":
            print(color_text("Exiting The Archive™", MAGENTA, bold=True))
            break

        top_results, expanded_terms = search_notes(query, notes, vocabulary)

        print(color_text("\nResults:", YELLOW, bold=True))

        if not top_results:
            print(color_text("No matches found.", RED, bold=True))
            continue

        for i, (score, note) in enumerate(top_results, start=1):
            preview = ""

            for term in expanded_terms:
                idx = note["body_search"].find(term)

                if idx != -1:
                    start = max(0, idx - 120)
                    end = min(len(note["body"]), idx + 220)

                    preview = note["body"][start:end]

                    if start > 0:
                        preview = "..." + preview
                    if end < len(note["body"]):
                        preview = preview + "..."

                    break

            # fallback if no body match found
            if not preview:
                preview = note["body"][:360]
                if len(note["body"]) > 360:
                    preview += "..."

            print(color_text(f"\n[{i}] {note['title']}", YELLOW, bold=True))
            print(color_text("Tags:", CYAN, bold=True), note["tags"])

            if note["aliases"]:
                print(color_text("Aliases:", CYAN, bold=True), note["aliases"])

            print(color_text("Score:", CYAN, bold=True), score)
            print(color_text("Path:", CYAN, bold=True), note["path"])

            highlighted_preview = highlight_text(preview, expanded_terms)
            print(color_text("Preview:", CYAN, bold=True), highlighted_preview)

            print(color_text("<>" * 35, YELLOW))

        choice = input(
            color_text(
                "\nEnter a result number to open, 'edit #' to edit, or press Enter to skip: ",
                MAGENTA,
                bold=True
            )
        ).strip()

        if choice == "":
            continue

        if choice.lower().startswith("edit "):
            parts = choice.split()

            if len(parts) != 2 or not parts[1].isdigit():
                print(color_text("Use format: edit 1", YELLOW, bold=True))
                continue

            choice_num = int(parts[1])

            if choice_num < 1 or choice_num > len(top_results):
                print(color_text("Number out of range.", RED, bold=True))
                continue

            selected_note = top_results[choice_num - 1][1]

            print(color_text("Opening editor for:", MAGENTA, bold=True), selected_note["path"])
            os.system(f'gedit "{selected_note["path"]}"')

            print(color_text("Reloading The Archive™...", RED, bold=True))
            notes = load_notes()
            vocabulary = build_vocabulary(notes)
            print(color_text("Reload complete.", GREEN, bold=True))
            continue

        if not choice.isdigit():
            print(color_text("Not a valid number.", RED, bold=True))
            continue

        choice_num = int(choice)

        if choice_num < 1 or choice_num > len(top_results):
            print(color_text("Number out of range.", RED, bold=True))
            continue

        selected_note = top_results[choice_num - 1][1]

        highlighted_body = highlight_text(selected_note["body"], expanded_terms)

        print("\n" + color_text("<>" * 35, YELLOW))
        print(color_text("FULL NOTE:", MAGENTA, bold=True), selected_note["title"])
        print(color_text("PATH:", CYAN, bold=True), selected_note["path"])
        print(color_text("TAGS:", CYAN, bold=True), selected_note["tags"])

        if selected_note["aliases"]:
            print(color_text("ALIASES:", CYAN, bold=True), selected_note["aliases"])

        print(color_text(". " * 35, YELLOW))
        print(highlighted_body)
        print(color_text("<>" * 35, YELLOW))
