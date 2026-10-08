"""Recognize explicit captions without mistaking arbitrary prose for tables."""
import re


NUMBERED_TABLE_CAPTION_PATTERN = re.compile(
    r"^\s*Table\s+(?:\d+(?:[.-]\d+)*[A-Za-z]?|[IVXLCDM]+)"
    r"(?:[.:])?(?:\s+.*)?$", re.I,
)

# Named numeric tables need no 'Table 1' prefix. Require an explicit range
# so mentions of tables in ordinary prose cannot create semantic boundaries.
NAMED_TABLE_CAPTION_PATTERN = re.compile(
    r"^\s*(?:[A-Za-z][A-Za-z'-]*\s+){1,10}Table\s+(?:for|of)\s+"
    r"\d[\d,]*\s+(?:to|through|[–—-])\s+\d[\d,]*\s*$", re.I,
)
PRIME_LIST_CAPTION_PATTERN = re.compile(
    r"^\s*Prime Numbers\s+from\s+\d[\d,]*\s+to\s+\d[\d,]*\s*$", re.I,
)
FLATTENED_NAMED_CAPTION_PATTERN = re.compile(
    r"^\s*((?:(?:[A-Za-z][A-Za-z'-]*\s+){1,10}Table\s+(?:for|of)|"
    r"Prime Numbers\s+from)\s+\d[\d,]*\s+(?:to|through|[–—-])\s+\d[\d,]*)"
    r"(?=\s|$)", re.I,
)


def is_table_caption(line):
    return any(pattern.fullmatch(line) for pattern in (
        NUMBERED_TABLE_CAPTION_PATTERN, NAMED_TABLE_CAPTION_PATTERN,
        PRIME_LIST_CAPTION_PATTERN,
    ))


def named_table_caption(text):
    """Recover a leading named caption even from older flattened chunks."""
    match = FLATTENED_NAMED_CAPTION_PATTERN.match(text or "")
    return match.group(1).strip() if match else None
