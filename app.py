from flask import Flask, request, render_template, redirect, url_for, jsonify
import os
import archive
from archive import load_notes, get_note_by_id, get_ingested_document, get_structural_index_for_document, get_structural_segment

app = Flask(__name__)

notes = archive.load_notes()
vocabulary = archive.build_vocabulary(notes)
folder_tree = archive.build_folder_tree()

def refresh_archive():
    global notes, vocabulary, folder_tree
    notes = archive.load_notes()
    vocabulary = archive.build_vocabulary(notes)
    folder_tree = archive.build_folder_tree()
    
def highlight_text_html(text, terms):
    highlighted = text

    for term in terms:
        if term:
            highlighted = highlighted.replace(
                term,
                f'<span class="highlight">{term}</span>'
            )

    return highlighted

@app.route("/", methods=["GET", "POST"])
def index():
    global notes, vocabulary
    refresh_archive()
    
    query = ""
    scope = "all"
    results = []
    expanded_terms = []
    message = ""

    if request.method == "POST":
        query = request.form.get("query", "").strip()
        scope = request.form.get("scope", "all").strip().lower()
        action = request.form.get("action", "search")

        if action == "reload":
            notes = archive.load_notes()
            vocabulary = archive.build_vocabulary(notes)
            message = "Reload complete."
        elif query:
            results, expanded_terms = archive.search_notes(query.lower(), notes, vocabulary, scope=scope)

            highlighted_results = []

            for score, note in results:
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

                if not preview:
                    preview = note["body"][:360]
                    if len(note["body"]) > 360:
                        preview += "..."

                highlighted_preview = highlight_text_html(preview, expanded_terms)

                note_display = note.copy()
                note_display["tags_display"] = ", ".join(note["tags"]) if note["tags"] else "—"
                note_display["aliases_display"] = ", ".join(note["aliases"]) if note["aliases"] else "—"

                highlighted_results.append((score, note_display, highlighted_preview))

            results = highlighted_results

    return render_template(
        "index.html",
        query=query,
        scope=scope,
        results=results,
        expanded_terms=expanded_terms,
        message=message
    )

@app.route("/api/note/<note_id>")
def api_note(note_id):
    notes = load_notes()

    note = get_note_by_id(note_id, notes)

    if note is None:
        return jsonify({
            "error": "note not found"
        }), 404

    return jsonify(note)

@app.route("/curator")
def curator_dashboard():
    return render_template("curator_dashboard.html")

@app.route("/curator/notes")
def curator_notes():
    global notes
    refresh_archive()

    def sort_key(note):
        meta = note.get("meta", {})

        chunk_index = meta.get("chunk_index")

        try:
            chunk_index = int(chunk_index)
        except (TypeError, ValueError):
            chunk_index = 999999

        return (
            note.get("category", ""),
            meta.get("source_doc_id", ""),
            note.get("title", "").lower(),
            chunk_index,
        )

    regular_notes = []
    system_notes = []
    structural_only_notes = []
    persistent_generated_notes = []

    for note in notes:
        meta = note.get("meta", {})
        category_parts = note.get("category_parts", [])

        if note.get("is_generated"):
            if meta.get("chunk_storage_mode") == "structural_only":
                structural_only_notes.append(note)
            else:
                persistent_generated_notes.append(note)

        elif category_parts[:1] == ["_system"]:
            system_notes.append(note)

        else:
            regular_notes.append(note)

    return render_template(
        "curator_notes.html",
        regular_notes=sorted(regular_notes, key=sort_key),
        system_notes=sorted(system_notes, key=sort_key),
        structural_only_notes=sorted(structural_only_notes, key=sort_key),
        persistent_generated_notes=sorted(persistent_generated_notes, key=sort_key),
    )

@app.route("/curator/documents")
def curator_documents():
    documents = archive.list_ingested_documents()
    return render_template("curator_documents.html", documents=documents)

@app.route("/curator/document/<doc_id>")
def curator_document(doc_id):
    document = archive.get_ingested_document(doc_id)

    if document is None:
        return "Document not found.", 404

    return render_template("curator_document.html", document=document)

@app.route("/curator/document/<doc_id>/source")
def curator_document_source(doc_id):
    global notes
    refresh_archive()

    note = archive.get_source_note_for_document(doc_id, notes)

    if note is None:
        return "Source document not available.", 404

    return redirect(url_for("source_document", note_id=note["id"]))

@app.route("/curator/document/<doc_id>/structure")
def curator_document_structure(doc_id):
    document = archive.get_structural_index_for_document(doc_id)

    if document is None:
        return "Structural index not available.", 404

    return render_template("structural_index.html", document=document)


@app.route("/curator/document/<doc_id>/structure/<int:entry_index>")
def curator_document_structure_entry(doc_id, entry_index):
    segment = archive.get_structural_segment(doc_id, entry_index)

    if segment is None:
        return "Structural segment not available.", 404

    return render_template("structural_segment.html", segment=segment)

@app.route("/curator/document/<doc_id>/reindex", methods=["GET", "POST"])
def curator_document_reindex(doc_id):
    document = archive.get_ingested_document(doc_id)

    if document is None:
        return "Document not found.", 404

    if request.method == "POST":
        result = archive.reindex_ingested_document(doc_id)
        updated_document = archive.get_ingested_document(doc_id)

        return render_template(
            "curator_action_result.html",
            title="Re-index Generated Output",
            result=result,
            document=updated_document
        )

    return render_template(
        "curator_confirm_action.html",
        title="Re-index Generated Output",
        action_description="Rebuild generated notes from the current metadata and chunk data for this document.",
        warning_text="This will replace the current generated output for this document, but it will not modify the archived source file or metadata record.",
        confirm_button_text="Re-index Generated Output",
        cancel_url=url_for("curator_document", doc_id=doc_id),
        form_action_url=url_for("curator_document_reindex", doc_id=doc_id),
        document=document
    )

@app.route("/curator/document/<doc_id>/delete-generated", methods=["GET", "POST"])
def curator_document_delete_generated(doc_id):
    document = archive.get_ingested_document(doc_id)

    if document is None:
        return "Document not found.", 404

    if request.method == "POST":
        result = archive.delete_generated_output(doc_id)
        updated_document = archive.get_ingested_document(doc_id)

        return render_template(
            "curator_action_result.html",
            title="Delete Generated Output",
            result=result,
            document=updated_document
        )

    return render_template(
        "curator_confirm_action.html",
        title="Delete Generated Output",
        action_description="Delete the generated notes/output directory for this document.",
        warning_text="This only removes generated output. It does not delete the archived source PDF, metadata, extracted text, cleaned text, or chunk data.",
        confirm_button_text="Delete Generated Output",
        cancel_url=url_for("curator_document", doc_id=doc_id),
        form_action_url=url_for("curator_document_delete_generated", doc_id=doc_id),
        document=document
    )

@app.route("/api/document/<doc_id>/structure")
def api_document_structure(doc_id):
    structural_document = get_structural_index_for_document(doc_id)

    if structural_document is None:
        return jsonify({
            "error": "structural index not found"
        }), 404

    return jsonify(structural_document)


@app.route("/api/document/<doc_id>/segment/<int:entry_index>")
def api_document_segment(doc_id, entry_index):
    segment = get_structural_segment(doc_id, entry_index)

    if segment is None:
        return jsonify({
            "error": "structural segment not found"
        }), 404

    return jsonify(segment)

@app.route("/api/document/<doc_id>")
def api_document(doc_id):
    document = get_ingested_document(doc_id)

    if document is None:
        return jsonify({
            "error": "document not found"
        }), 404

    return jsonify(document)

@app.route("/note/<int:note_id>")
def note_page(note_id):
    global notes
    refresh_archive()

    if note_id < 0 or note_id >= len(notes):
        return "Note not found", 404

    note = notes[note_id]
    return render_template("note.html", note=note)

@app.route("/context/<int:note_id>")
def source_context(note_id):
    global notes
    refresh_archive()

    if note_id < 0 or note_id >= len(notes):
        return "Note not found", 404

    note = notes[note_id]
    context = archive.get_source_context(note, notes)

    return render_template("source_context.html", context=context)

@app.route("/source/<int:note_id>")
def source_document(note_id):
    global notes
    refresh_archive()

    if note_id < 0 or note_id >= len(notes):
        return "Note not found", 404

    note = notes[note_id]
    document = archive.get_source_document(note, notes)

    if document is None:
        return "Source document not available.", 404

    return render_template("source_document.html", document=document)

@app.route("/edit/<int:note_id>", methods=["GET", "POST"])
def edit_note(note_id):
    global notes
    refresh_archive()

    if note_id < 0 or note_id >= len(notes):
        return "Note not found", 404

    note = notes[note_id]

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        tags = request.form.get("tags", "").strip()
        aliases = request.form.get("aliases", "").strip()
        body = request.form.get("body", "").strip()

        if not title or not body:
            return "Title and body are required.", 400

        archive.update_note(
            note["path"],
            title,
            tags,
            body,
            aliases
        )

        refresh_archive()

        for updated_note in notes:
            if updated_note["path"] == note["path"]:
                return redirect(f"/note/{updated_note['id']}")

        return "Updated note not found.", 500

    return render_template("edit_note.html", note=note)

@app.route("/curator/note/<int:note_id>/delete", methods=["GET", "POST"])
def curator_delete_note(note_id):
    global notes
    refresh_archive()

    if note_id < 0 or note_id >= len(notes):
        return "Note not found.", 404

    note = notes[note_id]

    if note.get("is_generated"):
        return "Generated notes should be managed through the document curator.", 400

    if request.method == "POST":
        result = archive.delete_note(note["path"])
        refresh_archive()

        return render_template(
            "curator_action_result.html",
            title="Delete Note",
            result=result,
            document=None
        )

    return render_template(
        "curator_confirm_action.html",
        title="Delete Note",
        action_description=f"Delete this note: {note['title']}",
        warning_text="This will permanently delete the note file. This cannot be undone unless you have a backup.",
        confirm_button_text="Delete Note",
        cancel_url=url_for("curator_notes"),
        form_action_url=url_for("curator_delete_note", note_id=note_id),
        document=None
    )

@app.route("/add", methods=["GET", "POST"])
def add_note():
    global notes, vocabulary, folder_tree

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        tags = request.form.get("tags", "").strip()
        aliases = request.form.get("aliases", "").strip()
        body = request.form.get("body", "").strip()
        category = request.form.get("category", "").strip()

        if not title or not body:
            return "Title and body are required.", 400

        saved_path = archive.save_note(title, tags, body, category, aliases)

        # reload archive
        notes = archive.load_notes()
        vocabulary = archive.build_vocabulary(notes)
        folder_tree = archive.build_folder_tree()

        # find the new note
        for note in notes:
            if note["path"] == saved_path:
                return redirect(f"/note/{note['id']}")

        return "Note saved but not found.", 500

    return render_template("add_note.html", folder_tree=folder_tree)

if __name__ == "__main__":
    app.run(debug=True)
