"""add offline analysis tables

Revision ID: 20260306_09
Revises: 20260228_08
Create Date: 2026-03-06 18:05:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260306_09"
down_revision: Union[str, None] = "20260228_08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "offline_analysis_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_ref", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_offline_analysis_tasks_source_type", "offline_analysis_tasks", ["source_type"], unique=False)
    op.create_index("ix_offline_analysis_tasks_status", "offline_analysis_tasks", ["status"], unique=False)
    op.create_index("ix_offline_analysis_tasks_severity", "offline_analysis_tasks", ["severity"], unique=False)
    op.create_index("ix_offline_analysis_tasks_created_at", "offline_analysis_tasks", ["created_at"], unique=False)

    op.create_table(
        "offline_analysis_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("matched_rules", sa.Text(), nullable=False),
        sa.Column("suggestions", sa.Text(), nullable=False),
        sa.Column("raw_excerpt", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_offline_analysis_results_task_id", "offline_analysis_results", ["task_id"], unique=False)
    op.create_index("ix_offline_analysis_results_created_at", "offline_analysis_results", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_offline_analysis_results_created_at", table_name="offline_analysis_results")
    op.drop_index("ix_offline_analysis_results_task_id", table_name="offline_analysis_results")
    op.drop_table("offline_analysis_results")

    op.drop_index("ix_offline_analysis_tasks_created_at", table_name="offline_analysis_tasks")
    op.drop_index("ix_offline_analysis_tasks_severity", table_name="offline_analysis_tasks")
    op.drop_index("ix_offline_analysis_tasks_status", table_name="offline_analysis_tasks")
    op.drop_index("ix_offline_analysis_tasks_source_type", table_name="offline_analysis_tasks")
    op.drop_table("offline_analysis_tasks")
