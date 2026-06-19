"""add assets table

Revision ID: 20260225_04
Revises: 20260225_03
Create Date: 2026-02-25 15:30:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260225_04"
down_revision: Union[str, None] = "20260225_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_code", sa.String(length=64), nullable=False, unique=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False, server_default="server"),
        sa.Column("system_id", sa.Integer(), sa.ForeignKey("systems.id"), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="in_use"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_assets_asset_code", "assets", ["asset_code"], unique=False)
    op.create_index("ix_assets_system_id", "assets", ["system_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_assets_system_id", table_name="assets")
    op.drop_index("ix_assets_asset_code", table_name="assets")
    op.drop_table("assets")
