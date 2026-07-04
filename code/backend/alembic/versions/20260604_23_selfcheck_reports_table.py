"""add selfcheck reports table

Revision ID: 20260604_23
Revises: 20260604_22
Create Date: 2026-06-04 23:55:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260604_23"
down_revision: Union[str, None] = "20260604_22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "selfcheck_reports"):
        op.create_table(
            "selfcheck_reports",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("system_id", sa.Integer(), sa.ForeignKey("systems.id"), nullable=False),
            sa.Column("system_code", sa.String(length=64), nullable=True),
            sa.Column("system_name", sa.String(length=128), nullable=True),
            sa.Column("range_minutes", sa.Integer(), nullable=True),
            sa.Column("alarm_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("payload_json", sa.Text(), nullable=False),
            sa.Column("checked_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_selfcheck_reports_system_id", "selfcheck_reports", ["system_id"], unique=False)
        op.create_index("ix_selfcheck_reports_checked_at", "selfcheck_reports", ["checked_at"], unique=False)


def downgrade() -> None:
    raise NotImplementedError("selfcheck reports migration is not intended to downgrade automatically")
