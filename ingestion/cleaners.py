from __future__ import annotations

from pathlib import Path
import re


def remove_soft_hyphens(text: str) -> str:
    """
    Remove soft hyphen characters that often appear in extracted PDF text.
    """
    return text.replace("\u00ad", "")


def repair_common_ligatures(text: str) -> str:
    """
    Repair common Unicode ligatures and extracted glyph substitutions.

    This is intentionally conservative and limited to very common cases.
    """
    replacements = {
        "ﬁ": "fi",
        "ﬂ": "fl",
        "ﬀ": "ff",
        "ﬃ": "ffi",
        "ﬄ": "ffl",
        "ﬅ": "ft",
        "ﬆ": "st",
    }

    for bad, good in replacements.items():
        text = text.replace(bad, good)

    return text


def normalize_common_unicode_punctuation(text: str) -> str:
    """
    Normalize a few common Unicode punctuation variants that often appear in PDFs.
    """
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u00a0": " ",
    }

    for bad, good in replacements.items():
        text = text.replace(bad, good)

    return text


def repair_linebreak_hyphenation(text: str) -> str:
    """
    Repair words split across lines with a hyphen.

    Example:
        'aera-\\ntion' -> 'aeration'
        'micro-\\ngrams' -> 'micrograms'
    """
    return re.sub(r"([A-Za-z])-\n([A-Za-z])", r"\1\2", text)


def normalize_line_endings(text: str) -> str:
    """
    Normalize CRLF/CR line endings to LF.
    """
    return text.replace("\r\n", "\n").replace("\r", "\n")


def normalize_inline_tabs(text: str) -> str:
    """
    Replace inline tab characters with single spaces.

    This helps with PDFs whose extracted text uses tabs between words,
    creating a fake columnar appearance in plain text.
    """
    return text.replace("\t", " ")


def collapse_whitespace(text: str) -> str:
    """
    Clean up excessive spaces while preserving paragraph/newline structure.
    """
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def repair_spaced_single_letters(text: str) -> str:
    """
    Repair obvious single-letter split artifacts inside words or short function words.

    Examples:
        'i s' -> 'is'
        't o' -> 'to'
        'a n d' -> 'and'   # via repeated application
    """
    previous = None
    current = text

    while current != previous:
        previous = current
        current = re.sub(r"\b([a-z]) ([a-z])\b", r"\1\2", current)

    return current


def repair_spaced_apostrophes(text: str) -> str:
    """
    Repair common extracted-text spacing around apostrophes.

    Examples:
        "wasn ' t" -> "wasn't"
        "I ' m" -> "I'm"
        "they ' re" -> "they're"
    """
    text = re.sub(r"\b([A-Za-z]+)\s+'\s+([A-Za-z]+)\b", r"\1'\2", text)
    text = re.sub(r"\b([A-Za-z]+)'\s+([A-Za-z]+)\b", r"\1'\2", text)
    text = re.sub(r"\b([A-Za-z]+)\s+'([A-Za-z]+)\b", r"\1'\2", text)
    return text


def repair_single_letter_prefix_splits(text: str) -> str:
    """
    Very conservative repair for cases like:
        'i ndicate' -> 'indicate'
        'l aboratory' -> 'laboratory'

    Only merges a single lowercase letter followed by a longer lowercase fragment.
    """
    return re.sub(r"\b([a-z]) ([a-z]{2,})\b", r"\1\2", text)


def clean_extracted_text(text: str) -> str:
    """
    Apply the deterministic cleaning pipeline.
    """
    text = normalize_line_endings(text)
    text = normalize_inline_tabs(text)
    text = remove_soft_hyphens(text)
    text = repair_common_ligatures(text)
    text = normalize_common_unicode_punctuation(text)
    text = repair_linebreak_hyphenation(text)
    text = repair_spaced_single_letters(text)
    text = repair_spaced_apostrophes(text)
    text = collapse_whitespace(text)
    return text


def save_cleaned_text(output_path: str | Path, text: str) -> Path:
    """
    Save cleaned text to disk as UTF-8.
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8") as f:
        f.write(text)

    return output_file
