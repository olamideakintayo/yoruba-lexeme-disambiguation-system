"""initial schema

Revision ID: 20260628_0001
Revises:
Create Date: 2026-06-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260628_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("license", sa.String(length=160), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "lexemes",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("canonical_form", sa.String(length=120), nullable=False),
        sa.Column("normalized_form", sa.String(length=120), nullable=False),
        sa.Column("language_code", sa.String(length=8), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lexemes_canonical_form", "lexemes", ["canonical_form"])
    op.create_index("ix_lexemes_normalized_form", "lexemes", ["normalized_form"])
    op.create_table(
        "search_logs",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("query", sa.String(length=160), nullable=False),
        sa.Column("normalized_query", sa.String(length=160), nullable=False),
        sa.Column("selected_lexeme_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["selected_lexeme_id"], ["lexemes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_search_logs_normalized_query", "search_logs", ["normalized_query"])
    op.create_table(
        "senses",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("lexeme_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("part_of_speech", sa.String(length=80), nullable=True),
        sa.Column("definition", sa.Text(), nullable=False),
        sa.Column("examples", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("domain", sa.String(length=120), nullable=True),
        sa.ForeignKeyConstraint(["lexeme_id"], ["lexemes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_senses_part_of_speech", "senses", ["part_of_speech"])
    op.create_table(
        "word_forms",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("lexeme_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("surface_form", sa.String(length=120), nullable=False),
        sa.Column("normalized_form", sa.String(length=120), nullable=False),
        sa.Column("tone_pattern", sa.String(length=80), nullable=False),
        sa.Column("diacritics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["lexeme_id"], ["lexemes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_word_forms_normalized_form", "word_forms", ["normalized_form"])
    op.create_index("ix_word_forms_surface_form", "word_forms", ["surface_form"])
    op.create_index(
        "ix_word_forms_normalized_form_trgm",
        "word_forms",
        ["normalized_form"],
        postgresql_using="gin",
        postgresql_ops={"normalized_form": "gin_trgm_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_word_forms_normalized_form_trgm", table_name="word_forms", postgresql_using="gin")
    op.drop_index("ix_word_forms_surface_form", table_name="word_forms")
    op.drop_index("ix_word_forms_normalized_form", table_name="word_forms")
    op.drop_table("word_forms")
    op.drop_index("ix_senses_part_of_speech", table_name="senses")
    op.drop_table("senses")
    op.drop_index("ix_search_logs_normalized_query", table_name="search_logs")
    op.drop_table("search_logs")
    op.drop_index("ix_lexemes_normalized_form", table_name="lexemes")
    op.drop_index("ix_lexemes_canonical_form", table_name="lexemes")
    op.drop_table("lexemes")
    op.drop_table("sources")
