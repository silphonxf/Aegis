"""add ai chat summaries table

Revision ID: 20260508_13
Revises: 20260508_12
Create Date: 2026-05-08 14:36:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260508_13"
down_revision: Union[str, None] = "20260508_12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_chat_summaries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.String(length=64), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("source_message_count", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_chat_summaries_id", "ai_chat_summaries", ["id"], unique=False)
    op.create_index("ix_ai_chat_summaries_conversation_id", "ai_chat_summaries", ["conversation_id"], unique=True)
    op.create_index("ix_ai_chat_summaries_updated_at", "ai_chat_summaries", ["updated_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ai_chat_summaries_updated_at", table_name="ai_chat_summaries")
    op.drop_index("ix_ai_chat_summaries_conversation_id", table_name="ai_chat_summaries")
    op.drop_index("ix_ai_chat_summaries_id", table_name="ai_chat_summaries")
    op.drop_table("ai_chat_summaries")
