from app.normalization import (
    clean_ocr_display_word,
    clean_ocr_meaning,
    describe_diacritics,
    detect_tone_pattern,
    is_displayable_yoruba_word,
    normalize_lookup,
    search_aliases,
    tone_label,
    tone_sort_key,
)


def test_normalize_lookup_removes_tones_and_dot_below() -> None:
    assert normalize_lookup("ow\u00f3") == "owo"
    assert normalize_lookup("\u00f2w\u00f2") == "owo"
    assert normalize_lookup("\u1ecd\u0300w\u1ecd\u0301") == "owo"
    assert normalize_lookup("\u1e62\u1eb9\u0301") == "se"


def test_detect_tone_pattern() -> None:
    assert detect_tone_pattern("ow\u00f3") == "mid-high"
    assert detect_tone_pattern("\u00f2w\u00f2") == "low-low"
    assert detect_tone_pattern("\u1ecd\u0300w\u1ecd\u0301") == "low-high"


def test_tone_label_and_sort_key() -> None:
    assert tone_label("owo") == "mid-mid"
    assert tone_label("\u00f3w\u00f3") == "high-high"
    assert tone_sort_key("low-low") < tone_sort_key("mid-mid") < tone_sort_key("high-high")
    assert tone_sort_key("high-low") > tone_sort_key("high-high")


def test_describe_diacritics() -> None:
    details = describe_diacritics("\u1ecd\u0300w\u1ecd\u0301")
    assert details["has_low_tone"] is True
    assert details["has_high_tone"] is True
    assert details["has_dot_below"] is True


def test_is_displayable_yoruba_word_accepts_real_yoruba_forms() -> None:
    assert is_displayable_yoruba_word("\u00f2w\u00f2") is True
    assert is_displayable_yoruba_word("ow\u00f3") is True
    assert is_displayable_yoruba_word("\u1ecd\u0301r\u1eb9\u0301") is True
    assert is_displayable_yoruba_word("\u1eb9\u0300k\u1ecd\u0300") is True


def test_is_displayable_yoruba_word_rejects_ocr_noise() -> None:
    assert is_displayable_yoruba_word("QWQ") is False
    assert is_displayable_yoruba_word("\u00d6WO") is False
    assert is_displayable_yoruba_word("Ab\u00e5") is False
    assert is_displayable_yoruba_word("A$#") is False


def test_clean_ocr_display_word_removes_latin_ocr_artifacts() -> None:
    assert clean_ocr_display_word("Ib\u00e5") == "Iba"
    assert clean_ocr_display_word("\u00d6WO") == "owo"
    assert clean_ocr_display_word("QWQ") == "owo"


def test_clean_ocr_meaning_removes_visible_artifacts() -> None:
    assert clean_ocr_meaning("kind. $") == "kind"
    assert clean_ocr_meaning("QWQ SQ mi") == "owo SO mi"
    assert clean_ocr_meaning("cup; 8 tumbler shaped; At4j\u00e5") == "cup; tumbler shaped; At4ja"


def test_search_aliases_include_ocr_cleanup() -> None:
    assert "owo" in search_aliases("QwQ")
    assert "owo" in search_aliases("\u00d6w\u00d6")
    assert "ase" in search_aliases("A$#")
