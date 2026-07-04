"""add firewall block configs

Revision ID: 20260604_24
Revises: 20260604_23
Create Date: 2026-06-04 23:58:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260604_24"
down_revision: Union[str, None] = "20260604_23"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "firewall_block_configs"):
        op.create_table(
            "firewall_block_configs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("scheme", sa.String(length=16), nullable=False, server_default="https"),
            sa.Column("firewall_ip", sa.String(length=128), nullable=False),
            sa.Column("port", sa.Integer(), nullable=False, server_default="443"),
            sa.Column("address_book_name", sa.String(length=128), nullable=False),
            sa.Column("username_encrypted", sa.String(length=2048), nullable=True),
            sa.Column("password_encrypted", sa.String(length=2048), nullable=True),
            sa.Column("verify_ssl", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="15"),
            sa.Column("addrbook_path", sa.String(length=128), nullable=False, server_default="/api/addrbook"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    raise NotImplementedError("firewall block config migration is not intended to downgrade automatically")
