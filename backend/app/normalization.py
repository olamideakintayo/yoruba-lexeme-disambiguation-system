from __future__ import annotations

import re
import unicodedata

LOW_TONE = "\u0300"
HIGH_TONE = "\u0301"
MID_TONE = "\u0304"
DOT_BELOW = "\u0323"
NASAL_MARK = "\u0303"
COMBINING_MARKS = {LOW_TONE, HIGH_TONE, MID_TONE, DOT_BELOW}

ALLOWED_YORUBA_BASE_LETTERS = set("abdefghijklmnoprstuwy\u1eb9\u1ecd\u1e63")
ALLOWED_WORD_PUNCTUATION = {"'", "\u2019", "-"}

OCR_SEARCH_REPLACEMENTS = str.maketrans(
    {
        "q": "o",
        "Q": "O",
        "\u00f6": "o",
        "\u00d6": "O",
        "\u00f8": "o",
        "\u00d8": "O",
        "\u00e5": "a",
        "\u00c5": "A",
        "\u00e4": "a",
        "\u00c4": "A",
        "\u00e6": "a",
        "\u00c6": "A",
        "$": "s",
        "#": "e",
        "8": "s",
        "0": "o",
        "1": "l",
    }
)

OCR_MEANING_TOKEN_REPLACEMENTS = str.maketrans(
    {
        "\u00f6": "o",
        "\u00d6": "O",
        "\u00f8": "o",
        "\u00d8": "O",
        "\u00e5": "a",
        "\u00c5": "A",
        "\u00e4": "a",
        "\u00c4": "A",
        "\u00e6": "a",
        "\u00c6": "A",
    }
)
OCR_JUNK_TOKEN_RE = re.compile(r"\b[\w]*[$#][\w]*\b|(?<!\w)[048](?!\w)")
OCR_QWQ_RE = re.compile(r"\b[qQ]([wW])[qQ]\b")
MULTISPACE_RE = re.compile(r"\s+")


def canonicalize(value: str) -> str:
    return unicodedata.normalize("NFC", value.strip())


def normalize_lookup(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.strip().casefold())
    without_marks = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return unicodedata.normalize("NFC", without_marks)


def normalize_ocr_lookup(value: str) -> str:
    cleaned = value.translate(OCR_SEARCH_REPLACEMENTS)
    return normalize_lookup(cleaned)


def clean_ocr_display_word(value: str) -> str:
    cleaned = normalize_lookup(value.translate(OCR_SEARCH_REPLACEMENTS))
    if value[:1].isupper() and not value.isupper():
        return cleaned.capitalize()
    return cleaned


def clean_ocr_meaning(value: str) -> str:
    cleaned = unicodedata.normalize("NFC", value.strip())
    cleaned = OCR_QWQ_RE.sub(lambda match: f"o{match.group(1).lower()}o", cleaned)
    cleaned = cleaned.translate(OCR_MEANING_TOKEN_REPLACEMENTS)
    cleaned = cleaned.replace("q", "o").replace("Q", "O")
    cleaned = OCR_JUNK_TOKEN_RE.sub("", cleaned)
    cleaned = cleaned.replace("$", "").replace("#", "")
    cleaned = cleaned.replace("—", "-")
    cleaned = MULTISPACE_RE.sub(" ", cleaned)
    return cleaned.strip(" ;,.-")


def search_aliases(value: str) -> set[str]:
    aliases = {normalize_lookup(value), normalize_ocr_lookup(value)}
    return {alias for alias in aliases if alias}


def is_displayable_yoruba_word(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return False

    decomposed = unicodedata.normalize("NFD", stripped)
    saw_letter = False
    for char in decomposed:
        if char.isspace() or char in ALLOWED_WORD_PUNCTUATION:
            continue
        if unicodedata.category(char) == "Mn":
            if char in {LOW_TONE, HIGH_TONE, MID_TONE, DOT_BELOW, NASAL_MARK}:
                continue
            return False
        if char.casefold() not in ALLOWED_YORUBA_BASE_LETTERS:
            return False
        saw_letter = True

    return saw_letter


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


def tone_label(value: str) -> str:
    pattern = detect_tone_pattern(value)
    return "mid" if pattern == "undetermined" else pattern


def tone_sort_key(pattern: str) -> tuple[int, str]:
    tones = [tone for tone in pattern.split("-") if tone and tone != "undetermined"]
    if tones and all(tone == "low" for tone in tones):
        return (0, pattern)
    if not tones or all(tone == "mid" for tone in tones):
        return (1, pattern)
    if tones and all(tone == "high" for tone in tones):
        return (2, pattern)
    return (3, pattern)


def describe_diacritics(value: str) -> dict[str, bool]:
    decomposed = unicodedata.normalize("NFD", value)
    return {
        "has_high_tone": HIGH_TONE in decomposed,
        "has_low_tone": LOW_TONE in decomposed,
        "has_mid_tone": MID_TONE in decomposed,
        "has_dot_below": DOT_BELOW in decomposed,
        "has_nasal": "n" in value.casefold() or NASAL_MARK in decomposed,
    }
