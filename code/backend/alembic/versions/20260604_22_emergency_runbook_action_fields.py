"""add emergency runbook action fields

Revision ID: 20260604_22
Revises: 20260604_21
Create Date: 2026-06-04 23:45:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260604_22"
down_revision = "20260604_21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("runbooks") as batch_op:
        batch_op.add_column(sa.Column("action_category", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("admin_user_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("process_name", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("default_process_id", sa.String(length=64), nullable=True))
        batch_op.create_foreign_key("fk_runbooks_admin_user_id_users", "users", ["admin_user_id"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("runbooks") as batch_op:
        batch_op.drop_constraint("fk_runbooks_admin_user_id_users", type_="foreignkey")
        batch_op.drop_column("default_process_id")
        batch_op.drop_column("process_name")
        batch_op.drop_column("admin_user_id")
        batch_op.drop_column("action_category")
