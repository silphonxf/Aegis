"""add room inspection config fields

Revision ID: 20260604_19
Revises: 20260603_18
Create Date: 2026-06-04 15:15:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260604_19"
down_revision: Union[str, None] = "20260603_18"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_column(inspector, "rooms", "qr_content"):
        op.add_column("rooms", sa.Column("qr_content", sa.String(length=255), nullable=True))
    if not _has_column(inspector, "rooms", "nfc_tag"):
        op.add_column("rooms", sa.Column("nfc_tag", sa.String(length=255), nullable=True))
    if not _has_column(inspector, "rooms", "check_items"):
        op.add_column("rooms", sa.Column("check_items", sa.Text(), nullable=True))

    record_system_id = next((col for col in inspector.get_columns("inspection_records") if col["name"] == "system_id"), None)
    if record_system_id and not record_system_id.get("nullable", True):
        with op.batch_alter_table("inspection_records") as batch_op:
            batch_op.alter_column("system_id", existing_type=sa.Integer(), nullable=True)

    rows = bind.execute(sa.text("SELECT id, room_code FROM rooms WHERE qr_content IS NULL OR TRIM(qr_content) = ''")).mappings().all()
    for row in rows:
        bind.execute(
            sa.text("UPDATE rooms SET qr_content = :qr_content WHERE id = :room_id"),
            {"qr_content": f"ROOM://{row['room_code']}", "room_id": row["id"]},
        )


def downgrade() -> None:
    raise NotImplementedError("room inspection config migration is not intended to downgrade automatically")
