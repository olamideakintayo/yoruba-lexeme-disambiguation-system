import json

from app.import_yoruba_pdf import (
    DEFAULT_YORUBA_ENGLISH_START_PAGE,
    convert_text_to_jsonl,
    parse_entries_from_text,
    write_jsonl,
)


OWO_MARKED = "\u1ecd\u0300w\u1ecd\u0301"
OWO_ACUTE = "ow\u00f3"
ORO_LOW = "\u1ecdr\u1ecd\u0300"
ABA_OCR = "Ab\u00e5"


def test_parse_entries_from_text_groups_multiline_definitions() -> None:
    text = f"""
    Part II
    Yoruba-English
    {OWO_ACUTE}, money; currency
    {ORO_LOW} - word, speech
      statement continued across a line
    """

    entries = parse_entries_from_text(text)

    assert entries[0]["word"] == OWO_ACUTE
    assert entries[0]["pos"] is None
    assert entries[0]["forms"] == [{"form": "owo"}, {"form": OWO_ACUTE}]
    assert entries[0]["senses"] == [
        {"glosses": ["money"], "examples": []},
        {"glosses": ["currency"], "examples": []},
    ]
    assert entries[1]["word"] == ORO_LOW
    assert entries[1]["forms"] == [{"form": "oro"}, {"form": ORO_LOW}]
    assert entries[1]["senses"] == [
        {"glosses": ["word, speech statement continued across a line"], "examples": []}
    ]


def test_parse_inline_ocr_entries() -> None:
    text = f"""
    --- Page 192 ---
    PART 11. YORUBA-ENGLISH. A, pro. him, her, it. {ABA_OCR}, n. attempt; endeavour.
    ABI Abiku, n. children who die in infancy. Abiye, adj. winged.
    Google
    """

    entries = parse_entries_from_text(text)

    assert [entry["word"] for entry in entries] == ["A", ABA_OCR, "Abiku", "Abiye"]
    assert entries[0]["pos"] == "pro"
    assert entries[1]["forms"] == [{"form": "aba"}, {"form": ABA_OCR}]
    assert entries[-1]["senses"] == [{"glosses": ["winged"], "examples": []}]


def test_write_jsonl_preserves_utf8(tmp_path) -> None:
    output = tmp_path / "dictionary.jsonl"
    entries = [
        {
            "word": OWO_MARKED,
            "pos": None,
            "forms": [{"form": "owo"}, {"form": OWO_MARKED}],
            "senses": [],
        }
    ]

    count = write_jsonl(entries, output)

    assert count == 1
    assert json.loads(output.read_text(encoding="utf-8"))["word"] == OWO_MARKED


def test_convert_text_to_jsonl(tmp_path) -> None:
    source = tmp_path / "ocr.txt"
    output = tmp_path / "dictionary.jsonl"
    source.write_text(f"{OWO_MARKED}, hand; arm\n", encoding="utf-8")

    count = convert_text_to_jsonl(source, output)

    assert count == 1
    entry = json.loads(output.read_text(encoding="utf-8").splitlines()[0])
    assert entry["word"] == OWO_MARKED
    assert entry["forms"] == [{"form": "owo"}, {"form": OWO_MARKED}]


def test_default_yoruba_english_start_page_matches_pdf_scan() -> None:
    assert DEFAULT_YORUBA_ENGLISH_START_PAGE == 192
