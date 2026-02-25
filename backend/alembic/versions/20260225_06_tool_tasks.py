"""add tool tasks table

Revision ID: 20260225_06
Revises: 20260225_05
Create Date: 2026-02-25 17:22:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260225_06"
down_revision: Union[str, None] = "20260225_05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tool_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("target", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_tool_tasks_action", "tool_tasks", ["action"], unique=False)
    op.create_index("ix_tool_tasks_status", "tool_tasks", ["status"], unique=False)
    op.create_index("ix_tool_tasks_created_at", "tool_tasks", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tool_tasks_created_at", table_name="tool_tasks")
    op.drop_index("ix_tool_tasks_status", table_name="tool_tasks")
    op.drop_index("ix_tool_tasks_action", table_name="tool_tasks")
    op.drop_table("tool_tasks")
