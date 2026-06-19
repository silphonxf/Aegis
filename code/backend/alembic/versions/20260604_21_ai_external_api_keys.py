"""add ai external api keys

Revision ID: 20260604_21
Revises: 20260604_20
Create Date: 2026-06-04 23:20:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260604_21"
down_revision: Union[str, None] = "20260604_20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "ai_external_api_keys"):
        op.create_table(
            "ai_external_api_keys",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("key_prefix", sa.String(length=24), nullable=False, index=True),
            sa.Column("key_hash", sa.String(length=128), nullable=False, unique=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("remark", sa.String(length=500), nullable=True),
            sa.Column("created_by", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("last_used_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    raise NotImplementedError("ai external api key migration is not intended to downgrade automatically")
