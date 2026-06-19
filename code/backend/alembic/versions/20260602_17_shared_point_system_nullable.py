"""allow shared inspection points without system binding

Revision ID: 20260602_17
Revises: 20260529_16
Create Date: 2026-06-02 22:55:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260602_17"
down_revision: Union[str, None] = "20260529_16"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("inspection_points") as batch_op:
        batch_op.alter_column(
            "system_id",
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade() -> None:
    raise NotImplementedError("shared point system nullable migration is not intended to downgrade automatically")
