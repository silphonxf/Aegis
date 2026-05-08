"""add ai chat messages table

Revision ID: 20260508_12
Revises: 20260508_11
Create Date: 2026-05-08 14:18:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260508_12"
down_revision: Union[str, None] = "20260508_11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_chat_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_chat_messages_id", "ai_chat_messages", ["id"], unique=False)
    op.create_index("ix_ai_chat_messages_conversation_id", "ai_chat_messages", ["conversation_id"], unique=False)
    op.create_index("ix_ai_chat_messages_created_at", "ai_chat_messages", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ai_chat_messages_created_at", table_name="ai_chat_messages")
    op.drop_index("ix_ai_chat_messages_conversation_id", table_name="ai_chat_messages")
    op.drop_index("ix_ai_chat_messages_id", table_name="ai_chat_messages")
    op.drop_table("ai_chat_messages")
