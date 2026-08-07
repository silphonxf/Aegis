"""repair IP block batch target snapshot columns

Revision ID: 20260806_28
Revises: 20260728_27
Create Date: 2026-08-06 22:36:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260806_28"
down_revision: Union[str, None] = "20260728_27"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(inspector, table_name: str):
    return {item["name"] for item in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "ip_block_batches" not in inspector.get_table_names():
        return

    columns = _column_names(inspector, "ip_block_batches")
    if "firewall_config_id" not in columns:
        # Keep the repair compatible with SQLite's ALTER TABLE limitations.
        # Application-level target snapshot validation still enforces that the
        # stored target id matches the live firewall configuration.
        op.add_column(
            "ip_block_batches",
            sa.Column("firewall_config_id", sa.Integer(), nullable=True),
        )
    if "firewall_host" not in columns:
        op.add_column(
            "ip_block_batches",
            sa.Column("firewall_host", sa.String(128), nullable=True),
        )


def downgrade() -> None:
    raise NotImplementedError("repair migration is not intended to downgrade automatically")
