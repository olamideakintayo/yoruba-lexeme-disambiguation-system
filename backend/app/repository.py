from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Lexeme, SearchLog, Sense, Source, WordForm, WordFormAlias
from app.normalization import (
    canonicalize,
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

SOURCE_PRIORITY = {
    "Online Yoruba Enrichment": 0,
    "Dictionary of the Yoruba Language": 1,
    "Kaikki/Wiktextract": 2,
    "Custom User Entries": 3,
}
CUSTOM_SOURCE_NAME = "Custom User Entries"
YORUBA_SEARCH_SOURCES = {"Online Yoruba Enrichment", "Dictionary of the Yoruba Language", CUSTOM_SOURCE_NAME}
YORUBA_ONLY_ERROR = "Only Yoruba dictionary words can be searched."
IGNORED_SEARCH_NORMALIZED_FORMS = {"am", "go"}

POS_LABELS = {
    "n": "noun",
    "v": "verb",
    "adj": "adjective",
    "adv": "adverb",
    "pro": "pronoun",
    "pron": "pronoun",
    "prep": "preposition",
    "conj": "conjunction",
    "inter": "interjection",
    "part": "particle",
}
VALID_TONES = {"low", "mid", "high"}


def source_priority(lexeme: Lexeme) -> int:
    if lexeme.source is None:
        return 9
    return SOURCE_PRIORITY.get(lexeme.source.name, 5)


def is_custom_lexeme(lexeme: Lexeme) -> bool:
    return lexeme.source is not None and lexeme.source.name == CUSTOM_SOURCE_NAME


def normalize_pos(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip().casefold().rstrip(".")
    return POS_LABELS.get(cleaned, cleaned)


def normalize_tone_pattern(value: str | None, fallback_word: str) -> str:
    cleaned = (value or "").strip().casefold()
    if not cleaned:
        return detect_tone_pattern(fallback_word)
    parts = [part.strip() for part in cleaned.replace(" ", "-").split("-") if part.strip()]
    if not parts or any(part not in VALID_TONES for part in parts):
        raise ValueError("Tone pattern must use low, mid, or high joined with hyphens, for example mid-high.")
    return "-".join(parts)


def tone_label_from_pattern(pattern: str, word: str) -> str:
    return pattern if pattern and pattern != "undetermined" else tone_label(word)


def is_ascii_plain_query(value: str) -> bool:
    stripped = value.strip()
    return bool(stripped) and stripped.isascii() and stripped.replace(" ", "").replace("-", "").replace("'", "").isalpha()


def is_noisy_ocr_word(value: str) -> bool:
    stripped = value.strip()
    if len(stripped) > 1 and stripped.isupper():
        return True
    return not is_displayable_yoruba_word(stripped)


def display_word_for_lexeme(lexeme: Lexeme, normalized_query: str) -> str | None:
    canonical = canonicalize(lexeme.canonical_form)
    if not is_noisy_ocr_word(canonical) and normalize_lookup(canonical) == normalized_query:
        return canonical
    if (
        not is_noisy_ocr_word(canonical)
        and is_displayable_yoruba_word(canonical)
        and any(form.normalized_form == normalized_query for form in lexeme.word_forms)
    ):
        return canonical

    for form in sorted(lexeme.word_forms, key=lambda item: (item.surface_form.islower(), item.surface_form)):
        surface = canonicalize(form.surface_form)
        if (
            form.normalized_form == normalized_query
            and not is_noisy_ocr_word(surface)
            and is_displayable_yoruba_word(surface)
        ):
            if canonical[:1].isupper() and surface.islower() and not canonical.isupper():
                return surface.capitalize()
            return surface

    cleaned = clean_ocr_display_word(canonical)
    if cleaned and normalize_lookup(cleaned) == normalized_query and is_displayable_yoruba_word(cleaned):
        return cleaned
    return None


def preferred_word_form(
    lexeme: Lexeme,
    display_word: str | None = None,
    normalized_query: str | None = None,
) -> WordForm | None:
    if not lexeme.word_forms:
        return None

    canonical = canonicalize(display_word or lexeme.canonical_form)
    normalized = normalized_query or normalize_lookup(canonical)
    forms = sorted(lexeme.word_forms, key=lambda form: (form.surface_form.casefold(), form.id or ""))

    for form in forms:
        if canonicalize(form.surface_form) == canonical:
            return form
    for form in forms:
        if form.normalized_form == normalized:
            return form
    return forms[0]


def lexeme_options() -> tuple:
    return (
        selectinload(Lexeme.source),
        selectinload(Lexeme.word_forms),
        selectinload(Lexeme.senses),
    )


async def get_or_create_source(
    session: AsyncSession,
    name: str,
    url: str | None = None,
    license_name: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Source:
    result = await session.execute(select(Source).where(Source.name == name))
    source = result.scalar_one_or_none()
    if source:
        return source

    source = Source(name=name, url=url, license=license_name, metadata_json=metadata or {})
    session.add(source)
    await session.flush()
    return source


async def get_custom_source(session: AsyncSession) -> Source:
    return await get_or_create_source(
        session,
        name=CUSTOM_SOURCE_NAME,
        url=None,
        license_name="User-provided custom entries",
        metadata={"source_type": "custom_user_entry"},
    )


async def import_entry(session: AsyncSession, entry: dict[str, Any], source: Source) -> Lexeme:
    word = canonicalize(entry.get("word") or entry.get("canonical_form") or "")
    if not word:
        raise ValueError("Dictionary entry is missing a word")

    normalized = normalize_lookup(word)
    result = await session.execute(
        select(Lexeme)
        .options(*lexeme_options())
        .where(Lexeme.canonical_form == word, Lexeme.source_id == source.id)
    )
    lexeme = result.scalar_one_or_none()

    if lexeme is None:
        lexeme = Lexeme(canonical_form=word, normalized_form=normalized, source=source)
        session.add(lexeme)
        await session.flush()

    forms = {word}
    for form in entry.get("forms", []):
        if isinstance(form, dict) and form.get("form"):
            forms.add(canonicalize(form["form"]))
        elif isinstance(form, str):
            forms.add(canonicalize(form))

    existing_forms_result = await session.execute(
        select(WordForm.surface_form).where(WordForm.lexeme_id == lexeme.id)
    )
    existing_forms = set(existing_forms_result.scalars().all())
    for surface_form in sorted(forms):
        if surface_form in existing_forms:
            continue
        word_form = WordForm(
            lexeme=lexeme,
            surface_form=surface_form,
            normalized_form=normalize_lookup(surface_form),
            tone_pattern=detect_tone_pattern(surface_form),
            diacritics=describe_diacritics(surface_form),
        )
        session.add(word_form)
        await session.flush()
        await upsert_word_form_aliases(session, word_form)

    existing_definitions_result = await session.execute(
        select(Sense.definition).where(Sense.lexeme_id == lexeme.id)
    )
    existing_definitions = set(existing_definitions_result.scalars().all())
    for sense_data in entry.get("senses", []):
        definitions = sense_data.get("glosses") or sense_data.get("raw_glosses") or []
        examples = sense_data.get("examples") or []
        tags = sense_data.get("tags") or []
        for definition in definitions:
            if not definition or definition in existing_definitions:
                continue
            session.add(
                Sense(
                    lexeme=lexeme,
                    part_of_speech=normalize_pos(entry.get("pos")),
                    definition=definition,
                    examples=examples,
                    domain=", ".join(tags) if tags else None,
                )
            )
            existing_definitions.add(definition)

    return lexeme


async def import_jsonl(session: AsyncSession, path: Path, source_name: str = "Kaikki/Wiktextract") -> int:
    is_local_yoruba_pdf = source_name == "Dictionary of the Yoruba Language"
    is_online_enrichment = source_name == "Online Yoruba Enrichment"
    source = await get_or_create_source(
        session,
        name=source_name,
        url=(
            None
            if is_local_yoruba_pdf
            else "https://en.wiktionary.org/wiki/Category:Yoruba_lemmas"
            if is_online_enrichment
            else "https://kaikki.org/dictionary/Yoruba/index.html"
        ),
        license_name=(
            "Local PDF source; verify public-domain/copyright status before redistribution"
            if is_local_yoruba_pdf
            else "Online lexical enrichment; verify source licenses before redistribution"
            if is_online_enrichment
            else "Wiktionary-derived; verify dump license before redistribution"
        ),
        metadata=(
            {
                "format": "jsonl",
                "source_type": "local_pdf",
                "section": "Part II Yoruba-English",
                "file": "backend/data/dictionary-of-the-yoruba-language.pdf",
            }
            if is_local_yoruba_pdf
            else {
                "format": "jsonl",
                "source_type": "curated_online_enrichment",
                "file": "backend/data/online_yoruba_enrichment.jsonl",
            }
            if is_online_enrichment
            else {"format": "jsonl"}
        ),
    )
    count = 0
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            await import_entry(session, json.loads(line), source)
            count += 1
    await session.commit()
    return count


async def upsert_word_form_aliases(session: AsyncSession, word_form: WordForm) -> None:
    existing_result = await session.execute(
        select(WordFormAlias.alias).where(WordFormAlias.word_form_id == word_form.id)
    )
    existing = set(existing_result.scalars().all())
    for alias in search_aliases(word_form.surface_form):
        if alias in existing:
            continue
        alias_type = "normalized" if alias == word_form.normalized_form else "ocr_cleanup"
        session.add(WordFormAlias(word_form=word_form, alias=alias, alias_type=alias_type))
        existing.add(alias)


async def backfill_word_form_aliases(session: AsyncSession) -> int:
    result = await session.execute(select(WordForm))
    word_forms = result.scalars().all()
    for word_form in word_forms:
        await upsert_word_form_aliases(session, word_form)
    await session.commit()
    return len(word_forms)


def custom_entry_payload(lexeme: Lexeme) -> dict[str, Any]:
    word = canonicalize(lexeme.canonical_form)
    first_form = preferred_word_form(lexeme, word)
    first_sense = lexeme.senses[0] if lexeme.senses else None
    examples = [example for example in ((first_sense.examples if first_sense else []) or []) if isinstance(example, dict)]
    tone_pattern = first_form.tone_pattern if first_form and first_form.tone_pattern else detect_tone_pattern(word)
    return {
        "id": lexeme.id,
        "word": word,
        "normalized_form": lexeme.normalized_form,
        "tone_pattern": tone_pattern,
        "tone_label": tone_label_from_pattern(tone_pattern, word),
        "meaning": first_sense.definition if first_sense else "",
        "part_of_speech": first_sense.part_of_speech if first_sense else None,
        "examples": examples,
    }


async def validate_custom_word(session: AsyncSession, word: str) -> dict[str, Any]:
    canonical = canonicalize(word)
    normalized = normalize_lookup(canonical)
    is_valid = bool(canonical) and not is_noisy_ocr_word(canonical) and is_displayable_yoruba_word(canonical)
    related_count = 0
    if normalized:
        result = await session.execute(
            select(Lexeme.id)
            .join(Source)
            .where(Lexeme.normalized_form == normalized, Source.name != CUSTOM_SOURCE_NAME)
            .limit(100)
        )
        related_count = len(result.scalars().all())

    warning = None
    if not is_valid:
        warning = "Enter a valid Yoruba word without OCR artifacts."
    elif related_count == 0:
        warning = "This normalized spelling was not found in the existing dictionary. Enable override to save it."

    return {
        "word": canonical,
        "normalized_form": normalized,
        "tone_pattern": detect_tone_pattern(canonical),
        "tone_label": tone_label(canonical),
        "is_valid_yoruba": is_valid,
        "related_dictionary_entries": related_count,
        "can_save_without_override": is_valid and related_count > 0,
        "warning": warning,
    }


async def list_custom_entries(session: AsyncSession) -> list[dict[str, Any]]:
    result = await session.execute(
        select(Lexeme)
        .options(*lexeme_options())
        .join(Source)
        .where(Source.name == CUSTOM_SOURCE_NAME)
        .order_by(Lexeme.created_at.desc(), Lexeme.canonical_form)
    )
    return [custom_entry_payload(lexeme) for lexeme in result.scalars().unique().all()]


async def create_custom_entry(session: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
    word = canonicalize(payload.get("word") or "")
    meaning = (payload.get("meaning") or "").strip()
    part_of_speech = normalize_pos(payload.get("part_of_speech"))
    tone_pattern = normalize_tone_pattern(payload.get("tone_pattern"), word)
    allow_override = bool(payload.get("allow_override"))
    if not word:
        raise ValueError("Word is required.")
    if not meaning:
        raise ValueError("Meaning is required.")

    validation = await validate_custom_word(session, word)
    if not validation["is_valid_yoruba"]:
        raise ValueError(validation["warning"] or "Enter a valid Yoruba word.")
    if validation["related_dictionary_entries"] == 0 and not allow_override:
        raise ValueError(validation["warning"] or "Enable override to save this word.")

    duplicate_result = await session.execute(
        select(Lexeme)
        .options(*lexeme_options())
        .join(Source)
        .where(Source.name == CUSTOM_SOURCE_NAME, Lexeme.canonical_form == word)
    )
    normalized_meaning = meaning.casefold()
    normalized_pos = (part_of_speech or "").casefold()
    for lexeme in duplicate_result.scalars().unique().all():
        for sense in lexeme.senses:
            if (
                sense.definition.strip().casefold() == normalized_meaning
                and (sense.part_of_speech or "").casefold() == normalized_pos
            ):
                raise ValueError("This custom entry already exists.")

    source = await get_custom_source(session)
    lexeme = Lexeme(canonical_form=word, normalized_form=validation["normalized_form"], source=source)
    session.add(lexeme)
    await session.flush()

    word_form = WordForm(
        lexeme=lexeme,
        surface_form=word,
        normalized_form=validation["normalized_form"],
        tone_pattern=tone_pattern,
        diacritics=describe_diacritics(word),
    )
    session.add(word_form)
    await session.flush()
    await upsert_word_form_aliases(session, word_form)

    examples = []
    example_text = (payload.get("example_text") or "").strip()
    example_english = (payload.get("example_english") or "").strip()
    if example_text:
        example: dict[str, str] = {"text": example_text}
        if example_english:
            example["english"] = example_english
        examples.append(example)

    session.add(Sense(lexeme=lexeme, part_of_speech=part_of_speech, definition=meaning, examples=examples))
    await session.commit()
    await session.refresh(lexeme)
    result = await session.execute(select(Lexeme).options(*lexeme_options()).where(Lexeme.id == lexeme.id))
    return custom_entry_payload(result.scalar_one())


async def delete_custom_entry(session: AsyncSession, lexeme_id: str) -> bool:
    result = await session.execute(
        select(Lexeme).options(*lexeme_options()).where(Lexeme.id == lexeme_id)
    )
    lexeme = result.scalar_one_or_none()
    if lexeme is None:
        return False
    if not is_custom_lexeme(lexeme):
        raise PermissionError("Only custom entries can be deleted.")
    await session.delete(lexeme)
    await session.commit()
    return True


async def search_lexemes(session: AsyncSession, query: str, limit: int = 20) -> tuple[list[dict[str, Any]], list[str]]:
    normalized_query = normalize_lookup(query)
    alias_queries = search_aliases(query)
    canonical_query = canonicalize(query)
    if not normalized_query:
        return [], []

    exact_query: Select[tuple[Lexeme]] = (
        select(Lexeme)
        .options(*lexeme_options())
        .join(WordForm)
        .outerjoin(WordFormAlias)
        .outerjoin(Source)
        .where(
            or_(
                WordForm.surface_form == canonical_query,
                WordForm.normalized_form == normalized_query,
                WordFormAlias.alias.in_(alias_queries),
                Lexeme.normalized_form == normalized_query,
            )
        )
        .order_by(Source.name != "Online Yoruba Enrichment", Lexeme.canonical_form)
        .limit(500)
    )
    prefix_query: Select[tuple[Lexeme]] = (
        select(Lexeme)
        .options(*lexeme_options())
        .join(WordForm)
        .outerjoin(WordFormAlias)
        .where(
            or_(
                WordForm.surface_form.ilike(f"%{canonical_query}%"),
                WordForm.normalized_form.ilike(f"{normalized_query}%"),
                *[WordFormAlias.alias.ilike(f"{alias}%") for alias in alias_queries],
                Lexeme.normalized_form.ilike(f"{normalized_query}%"),
            )
        )
        .limit(max(limit * 50, 1_000))
    )
    exact_result = await session.execute(exact_query)
    exact_lexemes = exact_result.scalars().unique().all()
    combined_lexemes = list(exact_lexemes)
    if len(exact_lexemes) < limit:
        prefix_result = await session.execute(prefix_query)
        combined_lexemes.extend(prefix_result.scalars().unique().all())
    lexemes = list({lexeme.id: lexeme for lexeme in combined_lexemes}.values())

    ranked: list[dict[str, Any]] = []
    for lexeme in lexemes:
        surfaces = {form.surface_form for form in lexeme.word_forms}
        normalized_forms = {form.normalized_form for form in lexeme.word_forms}
        if canonical_query in surfaces:
            rank = 1
            match_type = "exact"
        elif normalized_query in normalized_forms or lexeme.normalized_form == normalized_query:
            rank = 2
            match_type = "diacritic-insensitive"
        elif any(alias in search_aliases(form.surface_form) for form in lexeme.word_forms for alias in alias_queries):
            rank = 2
            match_type = "ocr-cleaned"
        else:
            rank = 3
            match_type = "prefix"
        ranked.append({"lexeme": lexeme, "rank": rank, "match_type": match_type})

    ranked.sort(
        key=lambda item: (
            source_priority(item["lexeme"]),
            item["rank"],
            item["lexeme"].canonical_form.casefold(),
        )
    )
    ranked = ranked[:limit]

    suggestion_candidates = [
        form.surface_form
        for item in ranked
        for form in item["lexeme"].word_forms
        if form.normalized_form.startswith(normalized_query)
        or bool(search_aliases(form.surface_form) & alias_queries)
    ]
    suggestions = list(dict.fromkeys(suggestion_candidates))[:8]

    session.add(SearchLog(query=query, normalized_query=normalized_query))
    await session.commit()

    return ranked, suggestions


async def search_tone_variants(session: AsyncSession, query: str, limit: int = 40) -> tuple[list[dict[str, Any]], list[str]]:
    normalized_query = normalize_lookup(query)
    if not normalized_query or normalized_query in IGNORED_SEARCH_NORMALIZED_FORMS:
        return [], []

    source_names = YORUBA_SEARCH_SOURCES

    result = await session.execute(
        select(Lexeme)
        .options(*lexeme_options())
        .join(WordForm)
        .join(Source)
        .where(
            or_(
                Lexeme.normalized_form == normalized_query,
                WordForm.normalized_form == normalized_query,
            ),
            Source.name.in_(source_names),
        )
    )
    lexemes = result.scalars().unique().all()

    variants_by_word: dict[tuple[str, str, str], dict[str, Any]] = {}
    for lexeme in lexemes:
        word = display_word_for_lexeme(lexeme, normalized_query)
        if word is None:
            continue

        is_custom = is_custom_lexeme(lexeme)
        custom_form = preferred_word_form(lexeme, word, normalized_query) if is_custom else None
        pattern = (
            custom_form.tone_pattern
            if custom_form is not None and custom_form.tone_pattern
            else detect_tone_pattern(word)
        )
        word_key = (
            word.casefold(),
            CUSTOM_SOURCE_NAME if is_custom else "built_in",
            lexeme.id if is_custom else "",
        )
        existing = variants_by_word.get(word_key)
        if existing is None:
            existing = {
                "word": word,
                "normalized_form": normalized_query,
                "tone_pattern": pattern,
                "tone_label": tone_label_from_pattern(pattern, word),
                "meaning": "",
                "meanings": [],
                "part_of_speech": None,
                "examples": [],
                "source": lexeme.source.name if lexeme.source else None,
                "source_priority": source_priority(lexeme),
            }
            variants_by_word[word_key] = existing
        elif source_priority(lexeme) < existing["source_priority"]:
            existing["word"] = word
            existing["tone_pattern"] = pattern
            existing["tone_label"] = tone_label_from_pattern(pattern, word)
            existing["source"] = lexeme.source.name if lexeme.source else None
            existing["source_priority"] = source_priority(lexeme)

        for sense in lexeme.senses:
            definition = clean_ocr_meaning(sense.definition)
            if not definition:
                continue
            examples = [example for example in (sense.examples or []) if isinstance(example, dict)]
            if definition not in existing["meanings"]:
                existing["meanings"].append(definition)
            if existing["part_of_speech"] is None and sense.part_of_speech:
                existing["part_of_speech"] = sense.part_of_speech
            existing["examples"].extend(example for example in examples if example not in existing["examples"])

    variants = list(variants_by_word.values())
    for item in variants:
        item["meaning"] = "; ".join(item["meanings"])
    variants.sort(
        key=lambda item: (
            item["source_priority"],
            tone_sort_key(item["tone_pattern"]),
            normalize_lookup(item["word"]),
            item["word"].casefold(),
        )
    )
    variants = variants[:limit]
    suggestions = list(dict.fromkeys(item["word"] for item in variants))[:8]

    session.add(SearchLog(query=query, normalized_query=normalized_query))
    await session.commit()

    return variants, suggestions


async def get_lexeme(session: AsyncSession, lexeme_id: str) -> Lexeme | None:
    result = await session.execute(
        select(Lexeme).options(*lexeme_options()).where(Lexeme.id == lexeme_id)
    )
    return result.scalar_one_or_none()
