"""add ai chat files table

Revision ID: 20260508_11
Revises: 20260405_10
Create Date: 2026-05-08 14:20:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260508_11"
down_revision: Union[str, None] = "20260405_10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_chat_files",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.String(length=64), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_chat_files_id", "ai_chat_files", ["id"], unique=False)
    op.create_index("ix_ai_chat_files_conversation_id", "ai_chat_files", ["conversation_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ai_chat_files_conversation_id", table_name="ai_chat_files")
    op.drop_index("ix_ai_chat_files_id", table_name="ai_chat_files")
    op.drop_table("ai_chat_files")
