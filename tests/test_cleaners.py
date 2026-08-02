from ingestion.cleaners import (
    clean_extracted_text,
    normalize_line_endings,
    remove_soft_hyphens,
    repair_common_ligatures,
    repair_linebreak_hyphenation,
    save_cleaned_text,
)


def test_normalize_line_endings():
    text = "line one\r\nline two\rline three"

    result = normalize_line_endings(text)

    assert result == "line one\nline two\nline three"


def test_remove_soft_hyphens():
    text = "micro\u00adcontroller"

    result = remove_soft_hyphens(text)

    assert result == "microcontroller"


def test_repair_common_ligatures():
    text = "ﬁle ﬂow oﬃce"

    result = repair_common_ligatures(text)

    assert result == "file flow office"


def test_repair_linebreak_hyphenation():
    text = "micro-\ncontroller"

    result = repair_linebreak_hyphenation(text)

    assert result == "microcontroller"


def test_clean_extracted_text_pipeline():
    raw_text = (
        "This\r\n"
        "is  a\tﬁle with\u00ad soft hyphens.\n\n\n"
        "The micro-\ncontroller wasn ' t ready."
    )

    result = clean_extracted_text(raw_text)

    assert result == (
        "This\n"
        "is a file with soft hyphens.\n\n"
        "The microcontroller wasn't ready."
    )


def test_save_cleaned_text(tmp_path):
    output_path = tmp_path / "nested" / "cleaned_text.txt"
    content = "Cleaned Archive text."

    result = save_cleaned_text(output_path, content)

    assert result == output_path
    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8") == content
