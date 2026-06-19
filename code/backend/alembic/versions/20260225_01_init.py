"""init tables

Revision ID: 20260225_01
Revises:
Create Date: 2026-02-25 11:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260225_01"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=False, unique=True),
        sa.Column("name", sa.String(length=64), nullable=False),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=64), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=False)

    op.create_table(
        "systems",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("system_code", sa.String(length=64), nullable=False, unique=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("env", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
    )

    op.create_table(
        "inspection_points",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("system_id", sa.Integer(), sa.ForeignKey("systems.id"), nullable=False),
        sa.Column("point_code", sa.String(length=64), nullable=False),
        sa.Column("qr_content", sa.String(length=255), nullable=False, unique=True),
        sa.Column("location", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_inspection_points_system_id", "inspection_points", ["system_id"], unique=False)

    op.create_table(
        "inspection_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("system_id", sa.Integer(), sa.ForeignKey("systems.id"), nullable=False),
        sa.Column("point_id", sa.Integer(), sa.ForeignKey("inspection_points.id"), nullable=False),
        sa.Column("inspector_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("result", sa.String(length=16), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("inspected_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_inspection_records_system_id", "inspection_records", ["system_id"], unique=False)
    op.create_index("ix_inspection_records_inspected_at", "inspection_records", ["inspected_at"], unique=False)

    op.create_table(
        "checklist_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("system_id", sa.Integer(), sa.ForeignKey("systems.id"), nullable=False),
        sa.Column("check_type", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
    )

    op.create_table(
        "selfcheck_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("system_id", sa.Integer(), sa.ForeignKey("systems.id"), nullable=False),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("checklist_templates.id"), nullable=False),
        sa.Column("operator_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("result", sa.String(length=16), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("checked_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_selfcheck_records_system_id", "selfcheck_records", ["system_id"], unique=False)
    op.create_index("ix_selfcheck_records_checked_at", "selfcheck_records", ["checked_at"], unique=False)

    op.create_table(
        "system_status_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("system_id", sa.Integer(), sa.ForeignKey("systems.id"), nullable=False),
        sa.Column("host_online", sa.String(length=16), nullable=False),
        sa.Column("port_ok", sa.String(length=16), nullable=False),
        sa.Column("cpu_level", sa.String(length=16), nullable=False),
        sa.Column("mem_level", sa.String(length=16), nullable=False),
        sa.Column("disk_level", sa.String(length=16), nullable=False),
        sa.Column("last_inspection_result", sa.String(length=16), nullable=False),
        sa.Column("last_selfcheck_result", sa.String(length=16), nullable=False),
        sa.Column("status_color", sa.String(length=16), nullable=False),
        sa.Column("captured_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_system_status_snapshots_system_id", "system_status_snapshots", ["system_id"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("resource", sa.String(length=64), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"], unique=False)
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"], unique=False)
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_system_status_snapshots_system_id", table_name="system_status_snapshots")
    op.drop_table("system_status_snapshots")

    op.drop_index("ix_selfcheck_records_checked_at", table_name="selfcheck_records")
    op.drop_index("ix_selfcheck_records_system_id", table_name="selfcheck_records")
    op.drop_table("selfcheck_records")

    op.drop_table("checklist_templates")

    op.drop_index("ix_inspection_records_inspected_at", table_name="inspection_records")
    op.drop_index("ix_inspection_records_system_id", table_name="inspection_records")
    op.drop_table("inspection_records")

    op.drop_index("ix_inspection_points_system_id", table_name="inspection_points")
    op.drop_table("inspection_points")

    op.drop_table("systems")

    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")

    op.drop_table("roles")
