from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    license: Mapped[str | None] = mapped_column(String(160))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lexemes: Mapped[list[Lexeme]] = relationship(back_populates="source")


class Lexeme(Base):
    __tablename__ = "lexemes"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    canonical_form: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_form: Mapped[str] = mapped_column(String(120), nullable=False)
    language_code: Mapped[str] = mapped_column(String(8), default="yo", nullable=False)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source: Mapped[Source | None] = relationship(back_populates="lexemes")
    word_forms: Mapped[list[WordForm]] = relationship(
        back_populates="lexeme", cascade="all, delete-orphan"
    )
    senses: Mapped[list[Sense]] = relationship(back_populates="lexeme", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_lexemes_normalized_form", "normalized_form"),
        Index("ix_lexemes_canonical_form", "canonical_form"),
    )


class WordForm(Base):
    __tablename__ = "word_forms"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    lexeme_id: Mapped[str] = mapped_column(ForeignKey("lexemes.id", ondelete="CASCADE"), nullable=False)
    surface_form: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_form: Mapped[str] = mapped_column(String(120), nullable=False)
    tone_pattern: Mapped[str] = mapped_column(String(80), default="undetermined", nullable=False)
    diacritics: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    lexeme: Mapped[Lexeme] = relationship(back_populates="word_forms")
    aliases: Mapped[list[WordFormAlias]] = relationship(
        back_populates="word_form", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_word_forms_normalized_form", "normalized_form"),
        Index("ix_word_forms_surface_form", "surface_form"),
    )


class WordFormAlias(Base):
    __tablename__ = "word_form_aliases"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    word_form_id: Mapped[str] = mapped_column(
        ForeignKey("word_forms.id", ondelete="CASCADE"), nullable=False
    )
    alias: Mapped[str] = mapped_column(String(120), nullable=False)
    alias_type: Mapped[str] = mapped_column(String(40), nullable=False)

    word_form: Mapped[WordForm] = relationship(back_populates="aliases")

    __table_args__ = (
        Index("ix_word_form_aliases_alias", "alias"),
        Index("ux_word_form_aliases_form_alias", "word_form_id", "alias", unique=True),
    )


class Sense(Base):
    __tablename__ = "senses"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    lexeme_id: Mapped[str] = mapped_column(ForeignKey("lexemes.id", ondelete="CASCADE"), nullable=False)
    part_of_speech: Mapped[str | None] = mapped_column(String(80))
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    examples: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    domain: Mapped[str | None] = mapped_column(String(120))

    lexeme: Mapped[Lexeme] = relationship(back_populates="senses")

    __table_args__ = (Index("ix_senses_part_of_speech", "part_of_speech"),)


class SearchLog(Base):
    __tablename__ = "search_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    query: Mapped[str] = mapped_column(String(160), nullable=False)
    normalized_query: Mapped[str] = mapped_column(String(160), nullable=False)
    selected_lexeme_id: Mapped[str | None] = mapped_column(ForeignKey("lexemes.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_search_logs_normalized_query", "normalized_query"),)
