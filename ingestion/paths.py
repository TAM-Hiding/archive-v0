from __future__ import annotations

from pathlib import Path
import re


# Root folder for all user-facing note/category paths
NOTES_ROOT = Path("notes")


def normalize_path(path_str: str) -> str:
    """
    Convert a user-entered category/path string into a clean, consistent path.

    Example:
        " Shop Math / Machining / Sine Bar " -> "shop_math/machining/sine_bar"

    Rules:
    - lowercase
    - trim surrounding whitespace
    - convert backslashes to forward slashes
    - collapse repeated slashes
    - convert spaces and hyphens inside path parts to underscores
    - remove most punctuation except underscores
    - drop empty path parts
    """
    if not isinstance(path_str, str):
        raise TypeError("path_str must be a string")

    cleaned = path_str.strip().lower()
    cleaned = cleaned.replace("\\", "/")
    cleaned = re.sub(r"/+", "/", cleaned)

    raw_parts = cleaned.split("/")
    normalized_parts: list[str] = []

    for part in raw_parts:
        part = part.strip()
        if not part:
            continue

        # Convert spaces and hyphens to underscores
        part = re.sub(r"[\s\-]+", "_", part)

        # Remove characters that are risky or annoying in paths
        part = re.sub(r"[^a-z0-9_]", "", part)

        # Collapse repeated underscores
        part = re.sub(r"_+", "_", part).strip("_")

        if part:
            normalized_parts.append(part)

    normalized = "/".join(normalized_parts)

    if not normalized:
        raise ValueError("Path is empty after normalization")

    return normalized


def validate_normalized_path(normalized_path: str) -> None:
    """
    Validate a normalized path before using it on disk.
    Raises ValueError if anything looks unsafe or malformed.
    """
    if not normalized_path:
        raise ValueError("Normalized path cannot be empty")

    if normalized_path.startswith("/") or normalized_path.endswith("/"):
        raise ValueError("Normalized path must not start or end with '/'")

    if "//" in normalized_path:
        raise ValueError("Normalized path must not contain repeated slashes")

    parts = normalized_path.split("/")
    if not parts:
        raise ValueError("Normalized path must contain at least one path part")

    for part in parts:
        if not part:
            raise ValueError("Normalized path contains an empty path part")

        if part in {".", ".."}:
            raise ValueError("Relative path components are not allowed")

        if not re.fullmatch(r"[a-z0-9_]+", part):
            raise ValueError(f"Invalid path part: {part}")


def get_category_path(root: Path | str, normalized_path: str) -> Path:
    """
    Return the absolute category path beneath the provided root.

    Example:
        root='notes', normalized_path='shop_math/machining'
        -> Path('notes/shop_math/machining')
    """
    validate_normalized_path(normalized_path)

    root_path = Path(root)
    category_path = root_path / normalized_path

    return category_path


def ensure_category_path_exists(root: Path | str, normalized_path: str) -> Path:
    """
    Ensure the normalized category path exists under the given root.
    Returns the created/resolved Path object.
    """
    category_path = get_category_path(root, normalized_path)
    category_path.mkdir(parents=True, exist_ok=True)
    return category_path


def normalize_and_ensure_path(path_str: str, root: Path | str = NOTES_ROOT) -> tuple[str, Path]:
    """
    Convenience helper:
    - normalize a raw user-entered path
    - validate it
    - create it on disk

    Returns:
        (normalized_path, category_path)
    """
    normalized = normalize_path(path_str)
    category_path = ensure_category_path_exists(root, normalized)
    return normalized, category_path
