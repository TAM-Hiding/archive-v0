from ingestion.extractors import extract_text_from_pdf, save_extracted_text
from ingestion.registry import read_metadata

METADATA_FILE = "notes/_archive_data/documents/20260408_143945_968692/metadata.json"

metadata = read_metadata(METADATA_FILE)
source_pdf = metadata["doc_root"] + "/" + metadata["stored_source_filename"]
output_txt = metadata["extracted_text_file"]

result = extract_text_from_pdf(source_pdf)
save_extracted_text(output_txt, result["text"])

print("Extraction successful.\n")
print(f"Extractor: {result['extractor']}")
print(f"Page count: {result['page_count']}")
print(f"Saved text to: {output_txt}")

print("\nPreview:\n")
print(result["text"][:1500])
