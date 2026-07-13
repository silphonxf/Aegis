"""add ai engine configs

Revision ID: 20260604_26
Revises: 20260604_25
Create Date: 2026-07-13 00:55:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260604_26"
down_revision: Union[str, None] = "20260604_25"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "ai_engine_configs"):
        op.create_table(
            "ai_engine_configs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("engine_type", sa.String(length=32), nullable=False, server_default="offline"),
            sa.Column("base_url", sa.String(length=255), nullable=True),
            sa.Column("api_key_encrypted", sa.String(length=2048), nullable=True),
            sa.Column("model", sa.String(length=128), nullable=True),
            sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="120"),
            sa.Column("chat_path", sa.String(length=128), nullable=True),
            sa.Column("diagnose_path", sa.String(length=128), nullable=True),
            sa.Column("log_analyze_path", sa.String(length=128), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    raise NotImplementedError("ai engine config migration is not intended to downgrade automatically")
