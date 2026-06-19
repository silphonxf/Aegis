"""extend tool task workflow fields

Revision ID: 20260405_10
Revises: 20260306_09
Create Date: 2026-04-05 15:15:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260405_10"
down_revision: Union[str, None] = "20260306_09"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tool_tasks", sa.Column("executor", sa.String(length=32), nullable=True))
    op.add_column("tool_tasks", sa.Column("started_at", sa.DateTime(), nullable=True))
    op.add_column("tool_tasks", sa.Column("finished_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("tool_tasks", "finished_at")
    op.drop_column("tool_tasks", "started_at")
    op.drop_column("tool_tasks", "executor")
