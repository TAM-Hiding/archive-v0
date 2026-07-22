from ingestion.paths import normalize_path, normalize_and_ensure_path


examples = [
    "Shop Math / Machining / Sine Bar",
    "general fab/304 prebend",
    "  tools//porta band  ",
    r"bronze\blackening\patina",
    "!!! weird ### path *** name !!!",
]

for example in examples:
    normalized = normalize_path(example)
    print(f"{example!r} -> {normalized!r}")

normalized, folder = normalize_and_ensure_path("Shop Math / Machining / Sine Bar")
print(f"\nCreated: {folder} (normalized: {normalized})")
