"""add nickname/avatar_url to users

Revision ID: 20260228_08
Revises: 20260225_07
Create Date: 2026-02-28 15:22:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260228_08"
down_revision: Union[str, None] = "20260225_07"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _safe_add_column(table: str, column: sa.Column) -> None:
    try:
        op.add_column(table, column)
    except Exception as e:
        msg = str(e).lower()
        if "already exists" in msg or "对象名" in msg or "重复" in msg:
            return
        raise


def _safe_drop_column(table: str, name: str) -> None:
    try:
        op.drop_column(table, name)
    except Exception as e:
        msg = str(e).lower()
        if "invalid column" in msg or "不存在" in msg:
            return
        raise


def upgrade() -> None:
    _safe_add_column("users", sa.Column("nickname", sa.String(length=64), nullable=True))
    _safe_add_column("users", sa.Column("avatar_url", sa.String(length=512), nullable=True))


def downgrade() -> None:
    _safe_drop_column("users", "avatar_url")
    _safe_drop_column("users", "nickname")
