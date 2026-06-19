"""add system selfcheck skill

Revision ID: 20260604_20
Revises: 20260604_19
Create Date: 2026-06-04 22:45:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260604_20"
down_revision: Union[str, None] = "20260604_19"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_column(inspector, "systems", "selfcheck_skill"):
        op.add_column("systems", sa.Column("selfcheck_skill", sa.Text(), nullable=True))


def downgrade() -> None:
    raise NotImplementedError("system selfcheck skill migration is not intended to downgrade automatically")
