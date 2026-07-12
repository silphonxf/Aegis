"""add room inspection count config

Revision ID: 20260604_25
Revises: 20260604_24
Create Date: 2026-07-13 00:25:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260604_25"
down_revision: Union[str, None] = "20260604_24"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_column(inspector, "rooms", "weekday_inspection_count"):
        op.add_column("rooms", sa.Column("weekday_inspection_count", sa.Integer(), nullable=False, server_default="1"))
    if not _has_column(inspector, "rooms", "holiday_inspection_count"):
        op.add_column("rooms", sa.Column("holiday_inspection_count", sa.Integer(), nullable=False, server_default="1"))


def downgrade() -> None:
    raise NotImplementedError("room inspection count migration is not intended to downgrade automatically")
