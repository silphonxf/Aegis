"""shared data phase1 base tables and columns

Revision ID: 20260529_15
Revises: 20260508_14
Create Date: 2026-05-29 10:35:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260529_15"
down_revision: Union[str, None] = "20260508_14"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "system_user_bindings"):
        op.create_table(
            "system_user_bindings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("system_id", sa.Integer(), sa.ForeignKey("systems.id"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("binding_role", sa.String(length=32), nullable=False),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_system_user_bindings_system_id", "system_user_bindings", ["system_id"], unique=False)
        op.create_index("ix_system_user_bindings_user_id", "system_user_bindings", ["user_id"], unique=False)
        op.create_index(
            "ux_system_user_bindings_unique_rel",
            "system_user_bindings",
            ["system_id", "user_id", "binding_role"],
            unique=True,
        )

    if not _has_table(inspector, "rooms"):
        op.create_table(
            "rooms",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("room_code", sa.String(length=64), nullable=False, unique=True),
            sa.Column("room_name", sa.String(length=128), nullable=False),
            sa.Column("building", sa.String(length=128), nullable=True),
            sa.Column("floor", sa.String(length=64), nullable=True),
            sa.Column("location_detail", sa.String(length=255), nullable=True),
            sa.Column("remark", sa.String(length=500), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    if not _has_table(inspector, "emergency_hosts"):
        op.create_table(
            "emergency_hosts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("host_code", sa.String(length=64), nullable=False, unique=True),
            sa.Column("host_name", sa.String(length=128), nullable=False),
            sa.Column("host_ip", sa.String(length=120), nullable=False),
            sa.Column("port", sa.Integer(), nullable=False),
            sa.Column("username", sa.String(length=64), nullable=False),
            sa.Column("auth_type", sa.String(length=32), nullable=False),
            sa.Column("password_ciphertext", sa.Text(), nullable=True),
            sa.Column("private_key_ciphertext", sa.Text(), nullable=True),
            sa.Column("private_key_passphrase_ciphertext", sa.Text(), nullable=True),
            sa.Column("connect_timeout_ms", sa.Integer(), nullable=False, server_default=sa.text("5000")),
            sa.Column("system_id", sa.Integer(), sa.ForeignKey("systems.id"), nullable=True),
            sa.Column("room_id", sa.Integer(), sa.ForeignKey("rooms.id"), nullable=True),
            sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("remark", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    if not _has_table(inspector, "runbooks"):
        op.create_table(
            "runbooks",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("runbook_code", sa.String(length=64), nullable=False, unique=True),
            sa.Column("runbook_name", sa.String(length=128), nullable=False),
            sa.Column("runbook_type", sa.String(length=32), nullable=False),
            sa.Column("system_id", sa.Integer(), sa.ForeignKey("systems.id"), nullable=True),
            sa.Column("target_host_id", sa.Integer(), sa.ForeignKey("emergency_hosts.id"), nullable=True),
            sa.Column("script_type", sa.String(length=32), nullable=False),
            sa.Column("script_body", sa.Text(), nullable=False),
            sa.Column("confirm_text", sa.String(length=500), nullable=True),
            sa.Column("risk_level", sa.String(length=32), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("remark", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    inspector = sa.inspect(bind)

    for table_name, columns in {
        "systems": [
            sa.Column("check_frequency", sa.String(length=32), nullable=True),
            sa.Column("remark", sa.String(length=500), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        ],
        "inspection_points": [
            sa.Column("room_id", sa.Integer(), nullable=True),
            sa.Column("point_name", sa.String(length=128), nullable=True),
            sa.Column("point_type", sa.String(length=32), nullable=True),
            sa.Column("nfc_tag", sa.String(length=255), nullable=True),
            sa.Column("location_detail", sa.String(length=255), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.text("1")),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        ],
        "inspection_records": [
            sa.Column("room_id", sa.Integer(), nullable=True),
            sa.Column("source", sa.String(length=32), nullable=True),
        ],
        "assets": [
            sa.Column("room_id", sa.Integer(), nullable=True),
            sa.Column("ip_address", sa.String(length=64), nullable=True),
            sa.Column("port", sa.Integer(), nullable=True),
            sa.Column("connection_type", sa.String(length=32), nullable=True),
            sa.Column("remark", sa.String(length=500), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        ],
        "selfcheck_records": [
            sa.Column("review_status", sa.String(length=16), nullable=True),
            sa.Column("reviewed_by", sa.Integer(), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        ],
    }.items():
        for column in columns:
            if not _has_column(inspector, table_name, column.name):
                op.add_column(table_name, column)
        inspector = sa.inspect(bind)

    if _has_table(inspector, "inspection_points") and not _has_index(inspector, "inspection_points", "ix_inspection_points_room_id"):
        op.create_index("ix_inspection_points_room_id", "inspection_points", ["room_id"], unique=False)
    if _has_table(inspector, "assets") and not _has_index(inspector, "assets", "ix_assets_room_id"):
        op.create_index("ix_assets_room_id", "assets", ["room_id"], unique=False)
    if _has_table(inspector, "inspection_records") and not _has_index(inspector, "inspection_records", "ix_inspection_records_room_id"):
        op.create_index("ix_inspection_records_room_id", "inspection_records", ["room_id"], unique=False)


def downgrade() -> None:
    raise NotImplementedError("shared data phase1 migration is not intended to downgrade automatically")
