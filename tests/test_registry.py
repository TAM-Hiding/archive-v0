from ingestion.registry import create_document_record

# Change this path if needed
SOURCE_FILE = "/home/strgzr/archive_v0/archive_raw_misc_reference/the-tell-tale-heart-edgar-allen-poe.pdf"
CATEGORY_PATH = "fiction/short_stories"

metadata = create_document_record(SOURCE_FILE, CATEGORY_PATH)

print("Document registered successfully.\n")
for key, value in metadata.items():
    print(f"{key}: {value}")
