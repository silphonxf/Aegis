"""ensure audit logs table exists for older deployments

Revision ID: 20260225_03
Revises: 20260225_02
Create Date: 2026-02-25 14:58:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260225_03"
down_revision: Union[str, None] = "20260225_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _index_exists(bind, table_name: str, index_name: str) -> bool:
    insp = sa.inspect(bind)
    indexes = insp.get_indexes(table_name)
    return any(idx.get("name") == index_name for idx in indexes)


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("audit_logs"):
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

    if not _index_exists(bind, "audit_logs", "ix_audit_logs_user_id"):
        op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"], unique=False)
    if not _index_exists(bind, "audit_logs", "ix_audit_logs_action"):
        op.create_index("ix_audit_logs_action", "audit_logs", ["action"], unique=False)
    if not _index_exists(bind, "audit_logs", "ix_audit_logs_created_at"):
        op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("audit_logs"):
        if _index_exists(bind, "audit_logs", "ix_audit_logs_created_at"):
            op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
        if _index_exists(bind, "audit_logs", "ix_audit_logs_action"):
            op.drop_index("ix_audit_logs_action", table_name="audit_logs")
        if _index_exists(bind, "audit_logs", "ix_audit_logs_user_id"):
            op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
        op.drop_table("audit_logs")
