"""add status rules table

Revision ID: 20260225_02
Revises: 20260225_01
Create Date: 2026-02-25 11:58:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260225_02"
down_revision: Union[str, None] = "20260225_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "status_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cpu_warn", sa.Integer(), nullable=False, server_default="70"),
        sa.Column("cpu_critical", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("mem_warn", sa.Integer(), nullable=False, server_default="75"),
        sa.Column("mem_critical", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("disk_warn", sa.Integer(), nullable=False, server_default="80"),
        sa.Column("disk_critical", sa.Integer(), nullable=False, server_default="95"),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("status_rules")
