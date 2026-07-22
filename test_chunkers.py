from pathlib import Path

from ingestion.chunkers import build_chunks, save_chunks
from ingestion.registry import read_metadata

METADATA_FILE = "notes/_archive_data/documents/20260408_143945_968692/metadata.json"

metadata = read_metadata(METADATA_FILE)
doc_id = metadata["doc_id"]
cleaned_text_path = Path(metadata["doc_root"]) / "cleaned_text.txt"
chunks_output_path = Path(metadata["chunks_file"])

cleaned_text = cleaned_text_path.read_text(encoding="utf-8")
chunks = build_chunks(doc_id, cleaned_text, max_chars=1200)
save_chunks(chunks_output_path, chunks)

print("Chunking successful.\n")
print(f"Doc ID: {doc_id}")
print(f"Chunk count: {len(chunks)}")
print(f"Saved chunks to: {chunks_output_path}")

print("\nFirst 3 chunks preview:\n")

for chunk in chunks[:3]:
    print("=" * 80)
    print(f"chunk_id: {chunk['chunk_id']}")
    print(f"chunk_index: {chunk['chunk_index']}")
    print(f"page_start: {chunk['page_start']}")
    print(f"section_heading: {chunk['section_heading']}")
    print(f"char_count: {chunk['char_count']}")
    print("\nTEXT PREVIEW:")
    print(chunk["text"][:600])
    print()
