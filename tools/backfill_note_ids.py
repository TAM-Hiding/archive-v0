from pathlib import Path
import argparse
import hashlib
import shutil
from datetime import datetime

NOTES_DIR = Path("notes")


def make_note_id(relative_path: Path) -> str:
    raw = str(relative_path).replace("\\", "/")
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"note_{digest}"


def split_metadata(text: str):
    lines = text.splitlines()
    metadata_lines = []
    body_start = 0

    for i, line in enumerate(lines):
        if line.strip() == "":
            body_start = i
            break
        metadata_lines.append(line)
    else:
        body_start = len(lines)

    body = "\n".join(lines[body_start:])
    return metadata_lines, body


def has_note_id(metadata_lines):
    for line in metadata_lines:
        key = line.split(":", 1)[0].strip().lower()
        if key in {"id", "note_id"}:
            return True
    return False


def insert_note_id(metadata_lines, note_id):
    new_lines = []
    inserted = False

    for line in metadata_lines:
        new_lines.append(line)
        key = line.split(":", 1)[0].strip().lower()

        if key == "title" and not inserted:
            new_lines.append(f"note_id: {note_id}")
            inserted = True

    if not inserted:
        new_lines.insert(0, f"note_id: {note_id}")

    return new_lines


def process_file(path: Path, apply: bool, backup: bool):
    text = path.read_text(encoding="utf-8")
    metadata_lines, body = split_metadata(text)

    if has_note_id(metadata_lines):
        return "skip", None

    relative_path = path.relative_to(NOTES_DIR)
    note_id = make_note_id(relative_path)
    new_metadata = insert_note_id(metadata_lines, note_id)
    new_text = "\n".join(new_metadata) + body

    if apply:
        if backup:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = path.with_suffix(path.suffix + f".bak_{timestamp}")
            shutil.copy2(path, backup_path)

        path.write_text(new_text, encoding="utf-8")

    return "update", note_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup", action="store_true")
    args = parser.parse_args()

    if not NOTES_DIR.exists():
        raise SystemExit("No notes/ directory found.")

    updated = 0
    skipped = 0

    for path in sorted(NOTES_DIR.rglob("*.md")):
        status, note_id = process_file(path, args.apply, args.backup)

        if status == "skip":
            skipped += 1
        else:
            updated += 1
            action = "UPDATED" if args.apply else "WOULD UPDATE"
            print(f"{action}: {path} -> {note_id}")

    print()
    print(f"Updated: {updated}" if args.apply else f"Would update: {updated}")
    print(f"Skipped: {skipped}")

    if not args.apply:
        print("\nDry run only. Re-run with --apply to write changes.")
        print("Recommended write mode:")
        print("python tools/backfill_note_ids.py --apply --backup")


if __name__ == "__main__":
    main()
