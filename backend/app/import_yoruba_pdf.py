from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader

from app.normalization import normalize_lookup

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_PDF_PATH = DATA_DIR / "dictionary-of-the-yoruba-language.pdf"
DEFAULT_OUTPUT_PATH = DATA_DIR / "yoruba_english_dictionary.jsonl"
DEFAULT_OCR_TEXT_PATH = DATA_DIR / "yoruba_english_ocr.txt"
DEFAULT_YORUBA_ENGLISH_START_PAGE = 192

YORUBA_LETTERS = "A-Za-zÀ-ÖØ-öø-ỹẸẹỌọṢṣḾḿǸǹ"
POS_TAGS = "n|v|adj|adv|pro|pron|prep|conj|inter|prefix|part"
ENTRY_START_RE = re.compile(
    rf"^(?P<headword>[{YORUBA_LETTERS}][{YORUBA_LETTERS}'\-]*(?:\s+[{YORUBA_LETTERS}][{YORUBA_LETTERS}'\-]*){{0,2}})"
    r"(?:\s*,\s*|\s+[-–—]\s+|\s{2,})(?P<definition>.+)$"
)
INLINE_ENTRY_RE = re.compile(
    rf"(?<![{YORUBA_LETTERS}0-9'’\-–—])"
    rf"(?P<headword>[{YORUBA_LETTERS}][{YORUBA_LETTERS}0-9$#&+'’*.\-–—]*)"
    rf"\s*,\s*(?P<pos>{POS_TAGS})\s*\.\s*",
    re.I,
)
NUMBERED_SENSE_RE = re.compile(r"(?:^|\s)(?:\d+[\.)])\s+")
SECTION_MARKER_RE = re.compile(r"(part\s*(?:ii|2).*yoruba\s*[- ]?\s*english|yoruba\s*[- ]?\s*english)", re.I)


class PdfImportError(RuntimeError):
    pass


def clean_text(value: str) -> str:
    value = value.replace("\u00ad", "")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def extract_pages(pdf_path: Path) -> list[str]:
    reader = PdfReader(str(pdf_path))
    return [clean_text(page.extract_text() or "") for page in reader.pages]


def find_yoruba_english_start_page(pages: list[str]) -> int | None:
    for index, text in enumerate(pages):
        if SECTION_MARKER_RE.search(text):
            return index
    return None


def selected_section_text(
    pages: list[str],
    start_page: int | None = None,
    end_page: int | None = None,
) -> str:
    if start_page is None:
        start_index = find_yoruba_english_start_page(pages)
        if start_index is None:
            extracted_chars = sum(len(page) for page in pages)
            if extracted_chars < 5_000:
                raise PdfImportError(
                    "Could not locate Part II Yoruba-English because this PDF appears to be scanned "
                    "or has no usable text layer. Run OCR first, then rerun this importer with a "
                    "text-layer PDF or provide extracted text."
                )
            raise PdfImportError(
                "Could not locate Part II Yoruba-English automatically. Rerun with --start-page "
                "and optionally --end-page."
            )
    else:
        if start_page < 1:
            raise PdfImportError("--start-page is 1-based and must be greater than 0.")
        start_index = start_page - 1

    stop_index = end_page if end_page is not None else len(pages)
    if stop_index < start_index + 1:
        raise PdfImportError("--end-page must be greater than or equal to --start-page.")

    return "\n".join(page for page in pages[start_index:stop_index] if page)


def is_probable_noise(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if stripped.isdigit():
        return True
    if stripped.startswith("--- Page ") and stripped.endswith("---"):
        return True
    lowered = stripped.casefold()
    return lowered in {
        "dictionary of the yoruba language",
        "yoruba-english",
        "yoruba english",
        "part ii",
    }


def split_senses(definition: str) -> list[str]:
    definition = definition.strip(" ;")
    if not definition:
        return []
    if NUMBERED_SENSE_RE.search(definition):
        senses = [part.strip(" ;") for part in NUMBERED_SENSE_RE.split(definition) if part.strip(" ;")]
        return senses or [definition]
    semicolon_parts = [part.strip() for part in definition.split(";") if part.strip()]
    return semicolon_parts if len(semicolon_parts) > 1 else [definition]


def strip_ocr_page_noise(text: str) -> str:
    text = re.sub(r"--- Page \d+ ---", " ", text)
    text = re.sub(r"\bGoogle\b", " ", text)
    text = re.sub(r"\bPART\s*1{1,2}\.?\s*YORUBA-ENGLISH\.?", " ", text, flags=re.I)
    # OCR often places running headers before the first entry on a page: "ABI Abiku, n. ..."
    text = re.sub(
        rf"\b\d*\s*[A-ZÀ-ÖØ-Þ]{{2,4}}\s+(?=[{YORUBA_LETTERS}][{YORUBA_LETTERS}0-9$#&+'’*.\-–—]*\s*,\s*(?:{POS_TAGS})\s*\.)",
        " ",
        text,
        flags=re.I,
    )
    return clean_text(text)


def build_entry(headword: str, pos: str | None, definition: str) -> dict[str, object] | None:
    headword = clean_text(headword.strip(" .;:-"))
    definition = clean_text(definition.strip(" .;:-"))
    if not headword or not definition:
        return None
    if len(headword) > 80 or any(char.isdigit() for char in headword):
        return None
    senses = [{"glosses": [sense], "examples": []} for sense in split_senses(definition)]
    if not senses:
        return None
    plain_form = normalize_lookup(headword)
    forms = [{"form": plain_form}] if plain_form and plain_form != headword else []
    forms.append({"form": headword})
    return {
        "word": headword,
        "pos": pos,
        "forms": forms,
        "senses": senses,
    }


def parse_inline_entries(text: str) -> list[dict[str, object]]:
    cleaned = strip_ocr_page_noise(text)
    matches = list(INLINE_ENTRY_RE.finditer(cleaned))
    entries: list[dict[str, object]] = []
    for index, match in enumerate(matches):
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(cleaned)
        definition = cleaned[match.end() : next_start]
        entry = build_entry(match.group("headword"), match.group("pos").casefold(), definition)
        if entry is not None:
            entries.append(entry)
    return entries


def parse_entries_from_text(text: str) -> list[dict[str, object]]:
    inline_entries = parse_inline_entries(text)
    if inline_entries:
        return inline_entries

    entries: list[dict[str, object]] = []
    current_word: str | None = None
    current_definition: list[str] = []

    def flush() -> None:
        nonlocal current_word, current_definition
        if current_word is None:
            return
        definition = clean_text(" ".join(current_definition))
        entry = build_entry(current_word, None, definition)
        if entry is not None:
            entries.append(entry)
        current_word = None
        current_definition = []

    for raw_line in text.splitlines():
        line = clean_text(raw_line)
        if is_probable_noise(line):
            continue
        match = ENTRY_START_RE.match(line)
        if match:
            flush()
            current_word = match.group("headword").strip()
            current_definition = [match.group("definition").strip()]
        elif current_word is not None:
            current_definition.append(line)

    flush()
    return entries


def write_jsonl(entries: Iterable[dict[str, object]], output_path: Path) -> int:
    count = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as file:
        for entry in entries:
            file.write(json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n")
            count += 1
    return count


def convert_pdf_to_jsonl(
    pdf_path: Path = DEFAULT_PDF_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    start_page: int | None = None,
    end_page: int | None = None,
) -> int:
    if not pdf_path.exists():
        raise PdfImportError(f"PDF not found: {pdf_path}")
    pages = extract_pages(pdf_path)
    section_text = selected_section_text(pages, start_page=start_page, end_page=end_page)
    entries = parse_entries_from_text(section_text)
    if not entries:
        raise PdfImportError(
            "No dictionary entries were parsed. The PDF text may need OCR cleanup or a more specific page range."
        )
    return write_jsonl(entries, output_path)


def convert_text_to_jsonl(text_path: Path, output_path: Path = DEFAULT_OUTPUT_PATH) -> int:
    if not text_path.exists():
        raise PdfImportError(f"Text file not found: {text_path}")
    entries = parse_entries_from_text(text_path.read_text(encoding="utf-8"))
    if not entries:
        raise PdfImportError("No dictionary entries were parsed from the text file.")
    return write_jsonl(entries, output_path)


async def _windows_ocr_image(image_path: Path) -> str:
    if sys.platform != "win32":
        raise PdfImportError("Built-in OCR mode currently uses Windows OCR and must run on Windows.")

    from winrt.windows.graphics.imaging import BitmapDecoder
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.storage import StorageFile

    file = await StorageFile.get_file_from_path_async(str(image_path.resolve()))
    stream = await file.open_read_async()
    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    engine = OcrEngine.try_create_from_user_profile_languages()
    if engine is None:
        raise PdfImportError("Windows OCR engine is unavailable for the current user profile language.")
    result = await engine.recognize_async(bitmap)
    return result.text


async def ocr_pdf_section_to_text(
    pdf_path: Path = DEFAULT_PDF_PATH,
    text_output_path: Path = DEFAULT_OCR_TEXT_PATH,
    start_page: int = DEFAULT_YORUBA_ENGLISH_START_PAGE,
    end_page: int | None = None,
    scale: float = 2.4,
) -> int:
    try:
        import fitz
    except ImportError as error:
        raise PdfImportError("PyMuPDF is required for OCR rendering. Install requirements.txt.") from error

    if not pdf_path.exists():
        raise PdfImportError(f"PDF not found: {pdf_path}")
    if start_page < 1:
        raise PdfImportError("--start-page is 1-based and must be greater than 0.")

    document = fitz.open(pdf_path)
    stop_page = end_page or document.page_count
    if stop_page < start_page:
        raise PdfImportError("--end-page must be greater than or equal to --start-page.")

    text_output_path.parent.mkdir(parents=True, exist_ok=True)
    rendered_pages = 0
    with tempfile.TemporaryDirectory() as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        with text_output_path.open("w", encoding="utf-8", newline="\n") as output:
            for page_number in range(start_page, stop_page + 1):
                page = document[page_number - 1]
                image_path = temp_dir / f"page-{page_number:04d}.png"
                pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                pixmap.save(image_path)
                text = await _windows_ocr_image(image_path)
                output.write(f"\n--- Page {page_number} ---\n")
                output.write(clean_text(text))
                output.write("\n")
                rendered_pages += 1
                if rendered_pages % 10 == 0:
                    print(f"OCR processed {rendered_pages} pages through PDF page {page_number}.")
    return rendered_pages


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert Part II Yoruba-English PDF entries to JSONL.")
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF_PATH)
    parser.add_argument("--text-file", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--ocr", action="store_true", help="OCR the scanned PDF before converting to JSONL.")
    parser.add_argument("--ocr-output", type=Path, default=DEFAULT_OCR_TEXT_PATH)
    parser.add_argument("--start-page", type=int, default=None)
    parser.add_argument("--end-page", type=int, default=None)
    parser.add_argument("--scale", type=float, default=2.4)
    args = parser.parse_args()

    try:
        if args.ocr:
            start_page = args.start_page or DEFAULT_YORUBA_ENGLISH_START_PAGE
            page_count = asyncio.run(
                ocr_pdf_section_to_text(
                    pdf_path=args.pdf,
                    text_output_path=args.ocr_output,
                    start_page=start_page,
                    end_page=args.end_page,
                    scale=args.scale,
                )
            )
            print(f"OCR wrote {page_count} pages to {args.ocr_output}")
            count = convert_text_to_jsonl(text_path=args.ocr_output, output_path=args.output)
        elif args.text_file is not None:
            count = convert_text_to_jsonl(text_path=args.text_file, output_path=args.output)
        else:
            count = convert_pdf_to_jsonl(
                pdf_path=args.pdf,
                output_path=args.output,
                start_page=args.start_page,
                end_page=args.end_page,
            )
    except PdfImportError as error:
        raise SystemExit(str(error)) from error

    print(f"Wrote {count} Yoruba-English entries to {args.output}")


if __name__ == "__main__":
    main()
