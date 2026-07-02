from app.models import Lexeme, Source, WordForm
from app.repository import (
    IGNORED_SEARCH_NORMALIZED_FORMS,
    display_word_for_lexeme,
    is_ascii_plain_query,
    is_noisy_ocr_word,
    source_priority,
)


def test_is_noisy_ocr_word_hides_ocr_artifacts() -> None:
    assert is_noisy_ocr_word("QWQ") is True
    assert is_noisy_ocr_word("\u00d6WO") is True
    assert is_noisy_ocr_word("OWO") is True
    assert is_noisy_ocr_word("A$#") is True


def test_is_noisy_ocr_word_allows_displayable_yoruba_words() -> None:
    assert is_noisy_ocr_word("ow\u00f3") is False
    assert is_noisy_ocr_word("\u00f2w\u00f2") is False
    assert is_noisy_ocr_word("\u1ecd\u0300w\u1ecd\u0301") is False
    assert is_noisy_ocr_word("Ogun") is False


def test_display_word_for_lexeme_uses_clean_plain_form_for_ocr_headword() -> None:
    lexeme = Lexeme(canonical_form="Ib\u00e5", normalized_form="iba")
    lexeme.word_forms = [
        WordForm(surface_form="Ib\u00e5", normalized_form="iba"),
        WordForm(surface_form="iba", normalized_form="iba"),
    ]

    assert display_word_for_lexeme(lexeme, "iba") == "Iba"


def test_display_word_for_lexeme_cleans_all_caps_ocr_headword() -> None:
    lexeme = Lexeme(canonical_form="QWQ", normalized_form="owo")
    lexeme.word_forms = [WordForm(surface_form="QWQ", normalized_form="owo")]

    assert display_word_for_lexeme(lexeme, "owo") == "owo"


def test_source_priority_prefers_clean_enrichment() -> None:
    enriched = Lexeme(canonical_form="ow\u00f3", normalized_form="owo")
    dictionary = Lexeme(canonical_form="owo", normalized_form="owo")
    enriched.source = Source(name="Online Yoruba Enrichment")
    dictionary.source = Source(name="Dictionary of the Yoruba Language")

    assert source_priority(enriched) < source_priority(dictionary)


def test_is_ascii_plain_query_detects_unmarked_input() -> None:
    assert is_ascii_plain_query("go") is True
    assert is_ascii_plain_query("IBA") is True
    assert is_ascii_plain_query("ẹṣin") is False
    assert is_ascii_plain_query("owó") is False
