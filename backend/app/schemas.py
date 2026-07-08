from typing import Any

from pydantic import BaseModel, Field


class SourceRead(BaseModel):
    name: str
    url: str | None = None
    license: str | None = None

    model_config = {"from_attributes": True}


class WordFormRead(BaseModel):
    id: str
    surface_form: str
    normalized_form: str
    tone_pattern: str
    diacritics: dict[str, Any]

    model_config = {"from_attributes": True}


class SenseRead(BaseModel):
    id: str
    part_of_speech: str | None = None
    definition: str
    examples: list[dict[str, Any]] = Field(default_factory=list)
    domain: str | None = None

    model_config = {"from_attributes": True}


class LexemeRead(BaseModel):
    id: str
    canonical_form: str
    normalized_form: str
    language_code: str
    source: SourceRead | None = None
    word_forms: list[WordFormRead]
    senses: list[SenseRead]

    model_config = {"from_attributes": True}


class SearchResult(BaseModel):
    lexeme: LexemeRead
    rank: int
    match_type: str


class ToneVariantResult(BaseModel):
    word: str
    normalized_form: str
    tone_pattern: str
    tone_label: str
    meaning: str
    meanings: list[str] = Field(default_factory=list)
    part_of_speech: str | None = None
    examples: list[dict[str, Any]] = Field(default_factory=list)
    source: str | None = None


class SearchResponse(BaseModel):
    query: str
    normalized_query: str
    results: list[ToneVariantResult]
    suggestions: list[str]
    error: str | None = None


class KeyboardResponse(BaseModel):
    alphabet: list[str]
    tones: list[dict[str, str]]
    controls: list[dict[str, str]]


class CustomEntryCreate(BaseModel):
    word: str
    meaning: str
    tone_pattern: str | None = None
    part_of_speech: str | None = None
    example_text: str | None = None
    example_english: str | None = None
    allow_override: bool = False


class CustomEntryRead(BaseModel):
    id: str
    word: str
    normalized_form: str
    tone_pattern: str
    tone_label: str
    meaning: str
    part_of_speech: str | None = None
    examples: list[dict[str, str]] = Field(default_factory=list)


class WordValidationRequest(BaseModel):
    word: str


class WordValidationResponse(BaseModel):
    word: str
    normalized_form: str
    tone_pattern: str
    tone_label: str
    is_valid_yoruba: bool
    related_dictionary_entries: int
    can_save_without_override: bool
    warning: str | None = None
