"""add ai conversations table

Revision ID: 20260508_14
Revises: 20260508_13
Create Date: 2026-05-08 15:05:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260508_14"
down_revision: Union[str, None] = "20260508_13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_conversations_id", "ai_conversations", ["id"], unique=False)
    op.create_index("ix_ai_conversations_conversation_id", "ai_conversations", ["conversation_id"], unique=True)
    op.create_index("ix_ai_conversations_created_at", "ai_conversations", ["created_at"], unique=False)
    op.create_index("ix_ai_conversations_updated_at", "ai_conversations", ["updated_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ai_conversations_updated_at", table_name="ai_conversations")
    op.drop_index("ix_ai_conversations_created_at", table_name="ai_conversations")
    op.drop_index("ix_ai_conversations_conversation_id", table_name="ai_conversations")
    op.drop_index("ix_ai_conversations_id", table_name="ai_conversations")
    op.drop_table("ai_conversations")
