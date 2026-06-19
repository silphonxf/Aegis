"""add ai diagnoses table

Revision ID: 20260225_07
Revises: 20260225_06
Create Date: 2026-02-25 17:28:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260225_07"
down_revision: Union[str, None] = "20260225_06"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_diagnoses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("suggestions", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ai_diagnoses_severity", "ai_diagnoses", ["severity"], unique=False)
    op.create_index("ix_ai_diagnoses_created_at", "ai_diagnoses", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ai_diagnoses_created_at", table_name="ai_diagnoses")
    op.drop_index("ix_ai_diagnoses_severity", table_name="ai_diagnoses")
    op.drop_table("ai_diagnoses")
