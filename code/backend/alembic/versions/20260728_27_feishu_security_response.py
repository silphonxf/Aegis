"""add Feishu security-response workflow

Revision ID: 20260728_27
Revises: 20260604_26
Create Date: 2026-07-28 10:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260728_27"
down_revision: Union[str, None] = "20260604_26"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(item["name"] == column_name for item in inspector.get_columns(table_name))


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    return any(item["name"] == index_name for item in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "firewall_block_configs"):
        additions = [
            ("target_code", sa.Column("target_code", sa.String(64), nullable=False, server_default="test-primary")),
            ("target_name", sa.Column("target_name", sa.String(128), nullable=False, server_default="山石测试设备")),
            ("is_default", sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("1"))),
            ("is_test_target", sa.Column("is_test_target", sa.Boolean(), nullable=False, server_default=sa.text("1"))),
        ]
        for name, column in additions:
            if not _has_column(inspector, "firewall_block_configs", name):
                op.add_column("firewall_block_configs", column)
        rows = bind.execute(
            sa.text("SELECT id FROM firewall_block_configs ORDER BY id ASC")
        ).fetchall()
        for position, row in enumerate(rows):
            target_code = "test-primary" if position == 0 else f"legacy-{row[0]}"
            bind.execute(
                sa.text("UPDATE firewall_block_configs SET target_code = :target_code WHERE id = :row_id"),
                {"target_code": target_code, "row_id": row[0]},
            )
        inspector = sa.inspect(bind)
        if not _has_index(inspector, "firewall_block_configs", "ix_firewall_block_configs_target_code"):
            op.create_index(
                "ix_firewall_block_configs_target_code",
                "firewall_block_configs",
                ["target_code"],
                unique=True,
            )

    if not _has_table(inspector, "feishu_user_bindings"):
        op.create_table(
            "feishu_user_bindings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("open_id", sa.String(128), nullable=False),
            sa.Column("union_id", sa.String(128), nullable=True),
            sa.Column("feishu_user_id", sa.String(128), nullable=True),
            sa.Column("display_name", sa.String(128), nullable=True),
            sa.Column("aegis_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("can_query", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("can_block", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_feishu_user_bindings_open_id", "feishu_user_bindings", ["open_id"], unique=True)

    if not _has_table(inspector, "feishu_event_receipts"):
        op.create_table(
            "feishu_event_receipts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("event_key", sa.String(255), nullable=False),
            sa.Column("event_type", sa.String(64), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="processing"),
            sa.Column("result_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_feishu_event_receipts_event_key", "feishu_event_receipts", ["event_key"], unique=True)

    if not _has_table(inspector, "ip_block_batches"):
        op.create_table(
            "ip_block_batches",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("status", sa.String(32), nullable=False, server_default="analyzed"),
            sa.Column("source", sa.String(32), nullable=False, server_default="feishu"),
            sa.Column("source_chat_id", sa.String(128), nullable=True),
            sa.Column("source_message_id", sa.String(128), nullable=True),
            sa.Column("requester_open_id", sa.String(128), nullable=True),
            sa.Column("requester_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("confirmer_open_id", sa.String(128), nullable=True),
            sa.Column("confirmer_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("firewall_config_id", sa.Integer(), sa.ForeignKey("firewall_block_configs.id"), nullable=True),
            sa.Column("firewall_target_code", sa.String(64), nullable=False, server_default="test-primary"),
            sa.Column("firewall_host", sa.String(128), nullable=True),
            sa.Column("address_book_name", sa.String(128), nullable=True),
            sa.Column("reason", sa.String(500), nullable=True),
            sa.Column("jinan_confirmed", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("analysis_json", sa.Text(), nullable=False),
            sa.Column("execution_json", sa.Text(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("executed_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_ip_block_batches_status", "ip_block_batches", ["status"], unique=False)

    if not _has_table(inspector, "ip_block_items"):
        op.create_table(
            "ip_block_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("batch_id", sa.String(36), sa.ForeignKey("ip_block_batches.id"), nullable=False),
            sa.Column("ip", sa.String(45), nullable=False),
            sa.Column("risk_level", sa.String(32), nullable=True),
            sa.Column("is_malicious", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("should_block", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("needs_jinan_confirmation", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("selected", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("status", sa.String(32), nullable=False, server_default="analyzed"),
            sa.Column("result_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("batch_id", "ip", name="uq_ip_block_items_batch_ip"),
        )
        op.create_index("ix_ip_block_items_batch_id", "ip_block_items", ["batch_id"], unique=False)


def downgrade() -> None:
    raise NotImplementedError("security-response migration is not intended to downgrade automatically")
