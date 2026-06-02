from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class InspectionPoint(Base):
    __tablename__ = "inspection_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("rooms.id"), nullable=True, index=True)
    system_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("systems.id"), nullable=True, index=True)
    point_code: Mapped[str] = mapped_column(String(64), nullable=False)
    point_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    point_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    qr_content: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    nfc_tag: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location_detail: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, default=True, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class InspectionRecord(Base):
    __tablename__ = "inspection_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    system_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("systems.id"), nullable=True, index=True)
    point_id: Mapped[int] = mapped_column(Integer, ForeignKey("inspection_points.id"), nullable=False)
    room_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("rooms.id"), nullable=True, index=True)
    inspector_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    result: Mapped[str] = mapped_column(String(16), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    inspected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
