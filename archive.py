import os
import json
import shutil
import string
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
                        "is_generated": is_generated
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
def search_notes(query, notes, vocabulary, scope="all"):
    translator = str.maketrans("", "", string.punctuation)
    clean_query = query.translate(translator)

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
        if scope == "notes" and note.get("is_generated"):
            continue
        if scope == "reference" and not note.get("is_generated"):
            continue

        score = 0
        
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
            "category_path": category_path,
            "status": metadata.get("status", ""),
            "chunk_count": metadata.get("chunk_count", 0),
            "page_count": metadata.get("page_count", 0),

            "chunk_storage_mode": metadata.get("chunk_storage_mode", ""),
            "chunk_count_estimate": metadata.get("chunk_count_estimate", 0),
            "structural_index_file": metadata.get("structural_index_file", ""),
            "structural_index_entry_count": metadata.get("structural_index_entry_count", 0),
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
        "entries": entries
    }


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

        char_start = entry.get("char_start")
        char_end = entry.get("char_end")

        if cleaned_text and char_start is not None and char_end is not None:
            try:
                body = cleaned_text[int(char_start):int(char_end)].strip()
            except (TypeError, ValueError):
                body = entry.get("preview", "")

        return {
            "entry": entry,
            "entry_index": index,
            "body": body,
        }

    return {
        "document": document,
        "previous": build_entry(entry_index - 1),
        "current": build_entry(entry_index),
        "next": build_entry(entry_index + 1)
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
