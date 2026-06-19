"""add usage percent fields to system_status_snapshots

Revision ID: 20260225_05
Revises: 20260225_04
Create Date: 2026-02-25 17:15:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260225_05"
down_revision: Union[str, None] = "20260225_04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("system_status_snapshots", sa.Column("cpu_usage", sa.Integer(), nullable=True))
    op.add_column("system_status_snapshots", sa.Column("mem_usage", sa.Integer(), nullable=True))
    op.add_column("system_status_snapshots", sa.Column("disk_usage", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("system_status_snapshots", "disk_usage")
    op.drop_column("system_status_snapshots", "mem_usage")
    op.drop_column("system_status_snapshots", "cpu_usage")
