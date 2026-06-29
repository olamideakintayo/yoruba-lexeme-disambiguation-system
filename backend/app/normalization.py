from __future__ import annotations

import unicodedata

LOW_TONE = "\u0300"
HIGH_TONE = "\u0301"
MID_TONE = "\u0304"
DOT_BELOW = "\u0323"
COMBINING_MARKS = {LOW_TONE, HIGH_TONE, MID_TONE, DOT_BELOW}

DOT_BELOW_MAP = {
    "ẹ": "e",
    "Ẹ": "E",
    "ọ": "o",
    "Ọ": "O",
    "ṣ": "s",
    "Ṣ": "S",
}


def canonicalize(value: str) -> str:
    return unicodedata.normalize("NFC", value.strip())


def normalize_lookup(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.strip().casefold())
    without_marks = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return unicodedata.normalize("NFC", without_marks)


OCR_SEARCH_REPLACEMENTS = str.maketrans(
    {
        "q": "o",
        "Q": "O",
        "ö": "o",
        "Ö": "O",
        "ø": "o",
        "Ø": "O",
        "å": "a",
        "Å": "A",
        "ä": "a",
        "Ä": "A",
        "æ": "ae",
        "Æ": "AE",
        "$": "s",
        "#": "e",
        "8": "s",
        "0": "o",
        "1": "l",
    }
)


def normalize_ocr_lookup(value: str) -> str:
    cleaned = value.translate(OCR_SEARCH_REPLACEMENTS)
    return normalize_lookup(cleaned)


def search_aliases(value: str) -> set[str]:
    aliases = {normalize_lookup(value), normalize_ocr_lookup(value)}
    return {alias for alias in aliases if alias}


def detect_tone_pattern(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value)
    tones: list[str] = []
    current_vowel_seen = False
    vowel_letters = set("aeiouAEIOU")

    for char in decomposed:
        if char in vowel_letters:
            if current_vowel_seen:
                tones.append("mid")
            current_vowel_seen = True
            continue

        if current_vowel_seen and char == HIGH_TONE:
            tones.append("high")
            current_vowel_seen = False
        elif current_vowel_seen and char == LOW_TONE:
            tones.append("low")
            current_vowel_seen = False
        elif current_vowel_seen and char == MID_TONE:
            tones.append("mid")
            current_vowel_seen = False
        elif unicodedata.category(char) != "Mn":
            if current_vowel_seen:
                tones.append("mid")
            current_vowel_seen = False

    if current_vowel_seen:
        tones.append("mid")

    return "-".join(tones) if tones else "undetermined"


def describe_diacritics(value: str) -> dict[str, bool]:
    decomposed = unicodedata.normalize("NFD", value)
    return {
        "has_high_tone": HIGH_TONE in decomposed,
        "has_low_tone": LOW_TONE in decomposed,
        "has_mid_tone": MID_TONE in decomposed,
        "has_dot_below": DOT_BELOW in decomposed,
        "has_nasal": "n" in value.casefold() or "\u0303" in decomposed,
    }
