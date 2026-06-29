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


class SearchResponse(BaseModel):
    query: str
    normalized_query: str
    results: list[SearchResult]
    suggestions: list[str]


class KeyboardResponse(BaseModel):
    alphabet: list[str]
    tones: list[dict[str, str]]
    controls: list[dict[str, str]]
