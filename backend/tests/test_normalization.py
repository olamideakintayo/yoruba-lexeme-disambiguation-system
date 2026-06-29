from app.normalization import describe_diacritics, detect_tone_pattern, normalize_lookup, search_aliases


def test_normalize_lookup_removes_tones_and_dot_below() -> None:
    assert normalize_lookup("ọ̀wọ́") == "owo"
    assert normalize_lookup("Ṣẹ́") == "se"


def test_detect_tone_pattern() -> None:
    assert detect_tone_pattern("owó") == "mid-high"
    assert detect_tone_pattern("òwò") == "low-low"


def test_describe_diacritics() -> None:
    details = describe_diacritics("ọ̀wọ́")
    assert details["has_low_tone"] is True
    assert details["has_high_tone"] is True
    assert details["has_dot_below"] is True


def test_search_aliases_include_ocr_cleanup() -> None:
    assert "owo" in search_aliases("QwQ")
    assert "owo" in search_aliases("ÖwÖ")
    assert "ase" in search_aliases("A$#")
