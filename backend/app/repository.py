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
    describe_diacritics,
    detect_tone_pattern,
    normalize_lookup,
    search_aliases,
)

SOURCE_PRIORITY = {
    "Online Yoruba Enrichment": 0,
    "Dictionary of the Yoruba Language": 1,
    "Kaikki/Wiktextract": 2,
}

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


def source_priority(lexeme: Lexeme) -> int:
    if lexeme.source is None:
        return 9
    return SOURCE_PRIORITY.get(lexeme.source.name, 5)


def normalize_pos(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip().casefold().rstrip(".")
    return POS_LABELS.get(cleaned, cleaned)


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


async def get_lexeme(session: AsyncSession, lexeme_id: str) -> Lexeme | None:
    result = await session.execute(
        select(Lexeme).options(*lexeme_options()).where(Lexeme.id == lexeme_id)
    )
    return result.scalar_one_or_none()
