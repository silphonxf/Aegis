"""shared data phase2 backfill legacy data

Revision ID: 20260529_16
Revises: 20260529_15
Create Date: 2026-05-29 10:42:00
"""

from typing import Sequence, Union
from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision: str = "20260529_16"
down_revision: Union[str, None] = "20260529_15"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _fetch_rows(conn, sql: str):
    return conn.execute(sa.text(sql)).mappings().all()


def upgrade() -> None:
    conn = op.get_bind()
    now = datetime.utcnow()

    rooms = {}
    existing_rooms = _fetch_rows(conn, "SELECT id, room_name FROM rooms")
    for row in existing_rooms:
        rooms[(row["room_name"] or "").strip()] = row["id"]

    raw_locations = []
    raw_locations.extend(
        _fetch_rows(conn, "SELECT DISTINCT location AS name FROM inspection_points WHERE location IS NOT NULL AND TRIM(location) <> ''")
    )
    raw_locations.extend(
        _fetch_rows(conn, "SELECT DISTINCT location AS name FROM assets WHERE location IS NOT NULL AND TRIM(location) <> ''")
    )

    next_room_no = len(rooms) + 1
    for row in raw_locations:
        room_name = (row["name"] or "").strip()
        if not room_name or room_name in rooms:
            continue
        room_code = f"ROOM_{next_room_no:04d}"
        inserted = conn.execute(
            sa.text(
                """
                INSERT INTO rooms (room_code, room_name, is_active, created_at, updated_at)
                VALUES (:room_code, :room_name, 1, :created_at, :updated_at)
                """
            ),
            {"room_code": room_code, "room_name": room_name, "created_at": now, "updated_at": now},
        )
        room_id = inserted.lastrowid
        if room_id is None:
            room_id = conn.execute(sa.text("SELECT id FROM rooms WHERE room_code = :room_code"), {"room_code": room_code}).scalar()
        rooms[room_name] = room_id
        next_room_no += 1

    for room_name, room_id in rooms.items():
        conn.execute(
            sa.text(
                """
                UPDATE inspection_points
                SET room_id = COALESCE(room_id, :room_id),
                    point_name = COALESCE(point_name, NULLIF(location, ''), point_code),
                    point_type = COALESCE(point_type, 'qr'),
                    location_detail = COALESCE(location_detail, location),
                    is_active = COALESCE(is_active, 1),
                    created_at = COALESCE(created_at, :created_at),
                    updated_at = COALESCE(updated_at, :updated_at)
                WHERE TRIM(COALESCE(location, '')) = :room_name
                """
            ),
            {"room_id": room_id, "room_name": room_name, "created_at": now, "updated_at": now},
        )
        conn.execute(
            sa.text(
                """
                UPDATE assets
                SET room_id = COALESCE(room_id, :room_id),
                    updated_at = COALESCE(updated_at, :updated_at)
                WHERE TRIM(COALESCE(location, '')) = :room_name
                """
            ),
            {"room_id": room_id, "room_name": room_name, "updated_at": now},
        )

    conn.execute(
        sa.text(
            """
            UPDATE inspection_records
            SET room_id = (
                SELECT ip.room_id FROM inspection_points ip WHERE ip.id = inspection_records.point_id
            )
            WHERE room_id IS NULL
            """
        )
    )
    conn.execute(
        sa.text("UPDATE inspection_records SET source = COALESCE(source, 'manual_migrated') WHERE source IS NULL")
    )

    conn.execute(
        sa.text(
            """
            UPDATE systems
            SET updated_at = COALESCE(updated_at, :updated_at)
            WHERE updated_at IS NULL
            """
        ),
        {"updated_at": now},
    )

    owner_rows = _fetch_rows(
        conn,
        "SELECT id AS system_id, owner_user_id FROM systems WHERE owner_user_id IS NOT NULL",
    )
    existing_bindings = {
        (row["system_id"], row["user_id"], row["binding_role"])
        for row in _fetch_rows(conn, "SELECT system_id, user_id, binding_role FROM system_user_bindings")
    }
    for row in owner_rows:
        key = (row["system_id"], row["owner_user_id"], "owner")
        if key in existing_bindings:
            continue
        conn.execute(
            sa.text(
                """
                INSERT INTO system_user_bindings (system_id, user_id, binding_role, is_primary, created_at)
                VALUES (:system_id, :user_id, 'owner', 1, :created_at)
                """
            ),
            {"system_id": row["system_id"], "user_id": row["owner_user_id"], "created_at": now},
        )


def downgrade() -> None:
    raise NotImplementedError("shared data backfill migration is not intended to downgrade automatically")
