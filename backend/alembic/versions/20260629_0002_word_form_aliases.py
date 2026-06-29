"""word form aliases

Revision ID: 20260629_0002
Revises: 20260628_0001
Create Date: 2026-06-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260629_0002"
down_revision: Union[str, None] = "20260628_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "word_form_aliases",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("word_form_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("alias", sa.String(length=120), nullable=False),
        sa.Column("alias_type", sa.String(length=40), nullable=False),
        sa.ForeignKeyConstraint(["word_form_id"], ["word_forms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_word_form_aliases_alias", "word_form_aliases", ["alias"])
    op.create_index(
        "ux_word_form_aliases_form_alias",
        "word_form_aliases",
        ["word_form_id", "alias"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ux_word_form_aliases_form_alias", table_name="word_form_aliases")
    op.drop_index("ix_word_form_aliases_alias", table_name="word_form_aliases")
    op.drop_table("word_form_aliases")
