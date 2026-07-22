from pathlib import Path

from ingestion.cleaners import clean_extracted_text, save_cleaned_text
from ingestion.registry import read_metadata

METADATA_FILE = "notes/_archive_data/documents/20260408_143945_968692/metadata.json"

metadata = read_metadata(METADATA_FILE)
raw_text_path = Path(metadata["extracted_text_file"])
cleaned_text_path = raw_text_path.parent / "cleaned_text.txt"

raw_text = raw_text_path.read_text(encoding="utf-8")
cleaned_text = clean_extracted_text(raw_text)
save_cleaned_text(cleaned_text_path, cleaned_text)

print("Cleaning successful.\n")
print(f"Raw text file: {raw_text_path}")
print(f"Cleaned text file: {cleaned_text_path}")

print("\nRAW PREVIEW:\n")
print(raw_text[:1200])

print("\n" + "=" * 80 + "\n")

print("CLEANED PREVIEW:\n")
print(cleaned_text[:1200])
