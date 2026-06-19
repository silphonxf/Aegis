"""add system host address and log configs

Revision ID: 20260603_18
Revises: 20260602_17
Create Date: 2026-06-03 11:05:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260603_18"
down_revision: Union[str, None] = "20260602_17"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_column(inspector, "systems", "host_address"):
        op.add_column("systems", sa.Column("host_address", sa.String(length=128), nullable=True))

    if not _has_table(inspector, "system_log_configs"):
        op.create_table(
            "system_log_configs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("system_id", sa.Integer(), sa.ForeignKey("systems.id"), nullable=False),
            sa.Column("log_name", sa.String(length=128), nullable=False),
            sa.Column("absolute_path", sa.String(length=500), nullable=False),
            sa.Column("log_level", sa.String(length=16), nullable=False, server_default="warning"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("remark", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_system_log_configs_system_id", "system_log_configs", ["system_id"], unique=False)


def downgrade() -> None:
    raise NotImplementedError("system host logs migration is not intended to downgrade automatically")
