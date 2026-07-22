from ingestion.indexer import index_chunks_to_generated_notes

METADATA_FILE = "notes/_archive_data/documents/20260408_143945_968692/metadata.json"

result = index_chunks_to_generated_notes(METADATA_FILE)

print("Indexing successful.\n")
print(f"doc_id: {result['doc_id']}")
print(f"category_path: {result['category_path']}")
print(f"output_dir: {result['output_dir']}")
print(f"note_count: {result['note_count']}")

print("\nFirst few files:\n")
for path in result["files"][:5]:
    print(path)
